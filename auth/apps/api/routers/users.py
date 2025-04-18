from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import UUID4
from sqlalchemy.orm import joinedload

from auth import schemas
from auth.crypto.access_token import generate_access_token
from auth.dependencies.admin_authentication import is_authenticated_admin_api
from auth.dependencies.logger import get_audit_logger
from auth.dependencies.pagination import PaginatedObjects
from auth.dependencies.permission import (
    UserPermissionsGetter,
    get_user_permissions_getter,
)
from auth.dependencies.repositories import get_repository
from auth.dependencies.user_roles import get_user_roles_service
from auth.dependencies.users import (
    get_admin_user_update,
    get_paginated_user_oauth_accounts,
    get_paginated_user_permissions,
    get_paginated_user_roles,
    get_paginated_users,
    get_user_by_id_or_404,
    get_user_create_admin,
    get_user_manager,
)
from auth.dependencies.webhooks import TriggerWebhooks, get_trigger_webhooks
from auth.errors import APIErrorCode
from auth.logger import AuditLogger
from auth.models import (
    AuditLogMessage,
    OAuthAccount,
    User,
    UserPermission,
    UserRole,
)
from auth.repositories import (
    ClientRepository,
    PermissionRepository,
    RoleRepository,
    TenantRepository,
    UserPermissionRepository,
    UserRepository,
)
from auth.schemas.generics import PaginatedResults
from auth.services.acr import ACR
from auth.services.user_manager import (
    InvalidPasswordError,
    UserAlreadyExistsError,
    UserManager,
)
from auth.services.user_roles import (
    UserRoleAlreadyExists,
    UserRoleDoesNotExist,
    UserRolesService,
)
from auth.services.webhooks.models import (
    UserDeleted,
    UserPermissionCreated,
    UserPermissionDeleted,
)

router = APIRouter(dependencies=[Depends(is_authenticated_admin_api)])


@router.get(
    "/", name="users:list", response_model=PaginatedResults[schemas.user.UserRead]
)
async def list_users(
    paginated_users: PaginatedObjects[User] = Depends(get_paginated_users),
) -> PaginatedResults[schemas.user.UserRead]:
    users, count = paginated_users
    return PaginatedResults(
        count=count,
        results=[schemas.user.UserRead.model_validate(user) for user in users],
    )


@router.get("/{id:uuid}", name="users:get", response_model=schemas.user.UserRead)
async def get_user(
    user: User = Depends(get_user_by_id_or_404),
) -> schemas.user.UserRead:
    return schemas.user.UserRead.model_validate(user)


@router.post(
    "/",
    name="users:create",
    response_model=schemas.user.UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    request: Request,
    user_create: schemas.user.UserCreateAdmin = Depends(get_user_create_admin),
    user_manager: UserManager = Depends(get_user_manager),
    user_repository: UserRepository = Depends(UserRepository),
    tenant_repository: TenantRepository = Depends(TenantRepository),
    audit_logger: AuditLogger = Depends(get_audit_logger),
):
    tenant = await tenant_repository.get_by_id(user_create.tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=APIErrorCode.USER_CREATE_UNKNOWN_TENANT,
        )

    try:
        created_user = await user_manager.create(
            user_create, user_create.tenant_id, request=request
        )
        audit_logger.log_object_write(AuditLogMessage.OBJECT_CREATED, created_user)
    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=APIErrorCode.USER_CREATE_ALREADY_EXISTS,
        ) from e
    except InvalidPasswordError as e:
        # Build a JSON response manually to fine-tune the response structure
        return JSONResponse(
            content={
                "detail": APIErrorCode.USER_CREATE_INVALID_PASSWORD,
                "reason": [str(message) for message in e.messages],
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user = await user_repository.get_by_id(created_user.id, (joinedload(User.tenant),))

    return schemas.user.UserRead.model_validate(user)


@router.patch("/{id:uuid}", name="users:update", response_model=schemas.user.UserRead)
async def update_user(
    request: Request,
    user_update: schemas.user.UserUpdateAdmin = Depends(get_admin_user_update),
    user: User = Depends(get_user_by_id_or_404),
    user_manager: UserManager = Depends(get_user_manager),
    audit_logger: AuditLogger = Depends(get_audit_logger),
):
    try:
        user = await user_manager.update(user_update, user, request=request)
        audit_logger.log_object_write(AuditLogMessage.OBJECT_UPDATED, user)
    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=APIErrorCode.USER_UPDATE_EMAIL_ALREADY_EXISTS,
        ) from e
    except InvalidPasswordError as e:
        # Build a JSON response manually to fine-tune the response structure
        return JSONResponse(
            content={
                "detail": APIErrorCode.USER_UPDATE_INVALID_PASSWORD,
                "reason": [str(message) for message in e.messages],
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return schemas.user.UserRead.model_validate(user)


@router.delete(
    "/{id:uuid}",
    name="users:delete",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_user(
    user: User = Depends(get_user_by_id_or_404),
    repository: UserRepository = Depends(UserRepository),
    audit_logger: AuditLogger = Depends(get_audit_logger),
    trigger_webhooks: TriggerWebhooks = Depends(get_trigger_webhooks),
):
    await repository.delete(user)
    audit_logger.log_object_write(AuditLogMessage.OBJECT_DELETED, user)
    trigger_webhooks(UserDeleted, user, schemas.user.UserRead)


@router.get(
    "/{id:uuid}/permissions",
    name="users:list_permissions",
    response_model=PaginatedResults[schemas.user_permission.UserPermission],
)
async def list_user_permissions(
    paginated_user_permissions: PaginatedObjects[UserPermission] = Depends(
        get_paginated_user_permissions
    ),
) -> PaginatedResults[schemas.user_permission.UserPermission]:
    user_permissions, count = paginated_user_permissions
    return PaginatedResults(
        count=count,
        results=[
            schemas.user_permission.UserPermission.model_validate(user_permission)
            for user_permission in user_permissions
        ],
    )


@router.post(
    "/{id:uuid}/access-token",
    name="users:access_token",
    response_model=schemas.user.AccessTokenResponse,
)
async def create_user_access_token(
    create_access_token: schemas.user.CreateAccessToken,
    user: User = Depends(get_user_by_id_or_404),
    get_user_permissions: UserPermissionsGetter = Depends(get_user_permissions_getter),
    client_repository: ClientRepository = Depends(ClientRepository),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> schemas.user.AccessTokenResponse:
    tenant = user.tenant

    client = await client_repository.get_by_id(create_access_token.client_id)
    if client is None or client.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=APIErrorCode.USER_CREATE_ACCESS_TOKEN_UNKNOWN_CLIENT,
        )

    tenant_host = tenant.get_host()
    permissions = await get_user_permissions(user)

    access_token = generate_access_token(
        user.tenant.get_sign_jwk(),
        tenant_host,
        client,
        datetime.now(UTC),
        ACR.LEVEL_ZERO,
        user,
        create_access_token.scopes,
        permissions,
        client.access_id_token_lifetime_seconds,
    )

    audit_logger(
        AuditLogMessage.USER_TOKEN_GENERATED_BY_ADMIN,
        subject_user_id=user.id,
        scope=create_access_token.scopes,
    )

    return schemas.user.AccessTokenResponse(
        access_token=access_token,
        expires_in=client.access_id_token_lifetime_seconds,
    )


@router.post(
    "/{id:uuid}/permissions",
    name="users:create_permission",
    status_code=status.HTTP_201_CREATED,
)
async def create_user_permission(
    user_permission_create: schemas.user_permission.UserPermissionCreate,
    user: User = Depends(get_user_by_id_or_404),
    permission_repository: PermissionRepository = Depends(
        get_repository(PermissionRepository)
    ),
    user_permission_repository: UserPermissionRepository = Depends(
        get_repository(UserPermissionRepository)
    ),
    audit_logger: AuditLogger = Depends(get_audit_logger),
    trigger_webhooks: TriggerWebhooks = Depends(get_trigger_webhooks),
) -> None:
    permission_id = user_permission_create.id
    permission = await permission_repository.get_by_id(permission_id)

    if permission is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=APIErrorCode.USER_PERMISSION_CREATE_NOT_EXISTING_PERMISSION,
        )

    existing_user_permission = (
        await user_permission_repository.get_by_permission_and_user(
            user.id, permission_id, direct_only=True
        )
    )
    if existing_user_permission is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=APIErrorCode.USER_PERMISSION_CREATE_ALREADY_ADDED_PERMISSION,
        )

    user_permission = UserPermission(user_id=user.id, permission=permission)
    await user_permission_repository.create(user_permission)
    audit_logger.log_object_write(
        AuditLogMessage.OBJECT_CREATED,
        user_permission,
        subject_user_id=user.id,
        permission_id=str(permission.id),
    )
    trigger_webhooks(
        UserPermissionCreated,
        user_permission,
        schemas.user_permission.UserPermission,
    )


@router.delete(
    "/{id:uuid}/permissions/{permission_id:uuid}",
    name="users:delete_permission",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_user_permission(
    permission_id: UUID4,
    user: User = Depends(get_user_by_id_or_404),
    user_permission_repository: UserPermissionRepository = Depends(
        get_repository(UserPermissionRepository)
    ),
    audit_logger: AuditLogger = Depends(get_audit_logger),
    trigger_webhooks: TriggerWebhooks = Depends(get_trigger_webhooks),
) -> None:
    user_permission = await user_permission_repository.get_by_permission_and_user(
        user.id, permission_id, direct_only=True
    )
    if user_permission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await user_permission_repository.delete(user_permission)
    audit_logger.log_object_write(
        AuditLogMessage.OBJECT_DELETED,
        user_permission,
        subject_user_id=user.id,
        permission_id=str(permission_id),
    )
    trigger_webhooks(
        UserPermissionDeleted,
        user_permission,
        schemas.user_permission.UserPermission,
    )


@router.get(
    "/{id:uuid}/roles",
    name="users:list_roles",
    response_model=PaginatedResults[schemas.user_role.UserRole],
)
async def list_user_roles(
    paginated_user_roles: PaginatedObjects[UserRole] = Depends(
        get_paginated_user_roles
    ),
) -> PaginatedResults[schemas.user_role.UserRole]:
    user_roles, count = paginated_user_roles
    return PaginatedResults(
        count=count,
        results=[
            schemas.user_role.UserRole.model_validate(user_role)
            for user_role in user_roles
        ],
    )


@router.post(
    "/{id:uuid}/roles", name="users:create_role", status_code=status.HTTP_201_CREATED
)
async def create_user_role(
    user_role_create: schemas.user_role.UserRoleCreate,
    user: User = Depends(get_user_by_id_or_404),
    role_repository: RoleRepository = Depends(get_repository(RoleRepository)),
    user_roles: UserRolesService = Depends(get_user_roles_service),
) -> None:
    role_id = user_role_create.id
    role = await role_repository.get_by_id(role_id)

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=APIErrorCode.USER_ROLE_CREATE_NOT_EXISTING_ROLE,
        )

    try:
        await user_roles.add_role(user, role)
    except UserRoleAlreadyExists as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=APIErrorCode.USER_ROLE_CREATE_ALREADY_ADDED_ROLE,
        ) from e


@router.delete(
    "/{id:uuid}/roles/{role_id:uuid}",
    name="users:delete_role",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_user_role(
    role_id: UUID4,
    user: User = Depends(get_user_by_id_or_404),
    role_repository: RoleRepository = Depends(get_repository(RoleRepository)),
    user_roles: UserRolesService = Depends(get_user_roles_service),
) -> None:
    role = await role_repository.get_by_id(role_id)

    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        await user_roles.delete_role(user, role)
    except UserRoleDoesNotExist as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from e


@router.get(
    "/{id:uuid}/oauth-accounts",
    name="users:list_oauth_accounts",
    response_model=PaginatedResults[schemas.oauth_account.OAuthAccount],
)
async def list_user_oauth_accounts(
    paginated_user_oauth_accounts: PaginatedObjects[OAuthAccount] = Depends(
        get_paginated_user_oauth_accounts
    ),
) -> PaginatedResults[schemas.oauth_account.OAuthAccount]:
    oauth_accounts, count = paginated_user_oauth_accounts
    return PaginatedResults(
        count=count,
        results=[
            schemas.oauth_account.OAuthAccount.model_validate(oauth_account)
            for oauth_account in oauth_accounts
        ],
    )
