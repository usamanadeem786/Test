from datetime import UTC, datetime
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.exceptions import RequestValidationError
from httpx_oauth.oauth2 import RefreshTokenError, RefreshTokenNotSupportedError
from pydantic import UUID4, ValidationError

from auth import schemas
from auth.dependencies.admin_authentication import is_authenticated_admin_api
from auth.dependencies.logger import get_audit_logger
from auth.dependencies.oauth_provider import (
    get_oauth_provider_by_id_or_404,
    get_paginated_oauth_providers,
)
from auth.dependencies.pagination import PaginatedObjects
from auth.dependencies.repositories import get_repository
from auth.dependencies.webhooks import TriggerWebhooks, get_trigger_webhooks
from auth.errors import APIErrorCode
from auth.logger import AuditLogger, logger
from auth.models import AuditLogMessage, OAuthProvider
from auth.models.oauth_account import OAuthAccount
from auth.repositories import (
    OAuthAccountRepository,
    OAuthProviderRepository,
    UserRepository,
)
from auth.schemas.generics import PaginatedResults
from auth.services.oauth_provider import get_oauth_provider_service
from auth.services.webhooks.models import (
    OAuthProviderCreated,
    OAuthProviderDeleted,
    OAuthProviderUpdated,
)

router = APIRouter(dependencies=[Depends(is_authenticated_admin_api)])


@router.get(
    "/",
    name="oauth_providers:list",
    response_model=PaginatedResults[schemas.oauth_provider.OAuthProvider],
)
async def list_oauth_providers(
    paginated_oauth_providers: PaginatedObjects[OAuthProvider] = Depends(
        get_paginated_oauth_providers
    ),
) -> PaginatedResults[schemas.oauth_provider.OAuthProvider]:
    oauth_providers, count = paginated_oauth_providers
    return PaginatedResults(
        count=count,
        results=[
            schemas.oauth_provider.OAuthProvider.model_validate(oauth_provider)
            for oauth_provider in oauth_providers
        ],
    )


@router.get(
    "/{id:uuid}",
    name="oauth_providers:get",
    response_model=schemas.oauth_provider.OAuthProvider,
)
async def get_oauth_provider(
    oauth_provider: OAuthProvider = Depends(get_oauth_provider_by_id_or_404),
) -> OAuthProvider:
    return oauth_provider


@router.post(
    "/",
    name="oauth_providers:create",
    response_model=schemas.oauth_provider.OAuthProvider,
    status_code=status.HTTP_201_CREATED,
)
async def create_oauth_provider(
    oauth_provider_create: schemas.oauth_provider.OAuthProviderCreate,
    repository: OAuthProviderRepository = Depends(
        get_repository(OAuthProviderRepository)
    ),
    audit_logger: AuditLogger = Depends(get_audit_logger),
    trigger_webhooks: TriggerWebhooks = Depends(get_trigger_webhooks),
) -> schemas.oauth_provider.OAuthProvider:
    oauth_provider = OAuthProvider(**oauth_provider_create.model_dump())
    oauth_provider = await repository.create(oauth_provider)
    audit_logger.log_object_write(AuditLogMessage.OBJECT_CREATED, oauth_provider)
    trigger_webhooks(
        OAuthProviderCreated,
        oauth_provider,
        schemas.oauth_provider.OAuthProvider,
    )

    return schemas.oauth_provider.OAuthProvider.model_validate(oauth_provider)


@router.patch(
    "/{id:uuid}",
    name="oauth_providers:update",
    response_model=schemas.oauth_provider.OAuthProvider,
)
async def update_oauth_provider(
    oauth_provider_update: schemas.oauth_provider.OAuthProviderUpdate,
    oauth_provider: OAuthProvider = Depends(get_oauth_provider_by_id_or_404),
    repository: OAuthProviderRepository = Depends(
        get_repository(OAuthProviderRepository)
    ),
    audit_logger: AuditLogger = Depends(get_audit_logger),
    trigger_webhooks: TriggerWebhooks = Depends(get_trigger_webhooks),
) -> schemas.oauth_provider.OAuthProvider:
    oauth_provider_update_dict = oauth_provider_update.model_dump(exclude_unset=True)

    try:
        oauth_provider_update_provider = (
            schemas.oauth_provider.OAuthProviderUpdateProvider.model_validate(
                oauth_provider
            )
        )
        schemas.oauth_provider.OAuthProviderUpdateProvider(
            **oauth_provider_update_provider.model_copy(
                update=oauth_provider_update_dict
            ).model_dump()
        )
    except ValidationError as e:
        raise RequestValidationError(e.errors()) from e

    for field, value in oauth_provider_update_dict.items():
        setattr(oauth_provider, field, value)

    await repository.update(oauth_provider)
    audit_logger.log_object_write(AuditLogMessage.OBJECT_UPDATED, oauth_provider)
    trigger_webhooks(
        OAuthProviderUpdated,
        oauth_provider,
        schemas.oauth_provider.OAuthProvider,
    )

    return schemas.oauth_provider.OAuthProvider.model_validate(oauth_provider)


@router.delete(
    "/{id:uuid}",
    name="oauth_providers:delete",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_oauth_provider(
    oauth_provider: OAuthProvider = Depends(get_oauth_provider_by_id_or_404),
    repository: OAuthProviderRepository = Depends(
        get_repository(OAuthProviderRepository)
    ),
    audit_logger: AuditLogger = Depends(get_audit_logger),
    trigger_webhooks: TriggerWebhooks = Depends(get_trigger_webhooks),
):
    await repository.delete(oauth_provider)
    audit_logger.log_object_write(AuditLogMessage.OBJECT_DELETED, oauth_provider)
    trigger_webhooks(
        OAuthProviderDeleted,
        oauth_provider,
        schemas.oauth_provider.OAuthProvider,
    )


@router.get(
    "/{id:uuid}/access-token/{user_id:uuid}",
    name="oauth_providers:get_user_access_token",
    response_model=schemas.oauth_account.OAuthAccountAccessToken,
)
async def get_user_access_token(
    user_id: UUID4,
    oauth_provider: OAuthProvider = Depends(get_oauth_provider_by_id_or_404),
    oauth_account_repository: OAuthAccountRepository = Depends(
        get_repository(OAuthAccountRepository)
    ),
    user_repository: UserRepository = Depends(UserRepository),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> OAuthAccount:
    user = await user_repository.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    oauth_account = await oauth_account_repository.get_by_provider_and_user(
        oauth_provider.id, user.id
    )
    if oauth_account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if oauth_account.is_expired():
        oauth_provider_service = get_oauth_provider_service(oauth_provider)
        try:
            access_token_dict = await oauth_provider_service.refresh_token(
                cast(str, oauth_account.refresh_token)
            )
        except RefreshTokenNotSupportedError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=APIErrorCode.OAUTH_PROVIDER_REFRESH_TOKEN_NOT_SUPPORTED,
            ) from e
        except RefreshTokenError as e:
            logger.warning(
                "Error while refreshing OAuth Provider access token",
                message=e.message,
                error_body=e.response.text if e.response is not None else None,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=APIErrorCode.OAUTH_PROVIDER_REFRESH_TOKEN_ERROR,
            ) from e
        oauth_account.access_token = access_token_dict["access_token"]
        try:
            oauth_account.expires_at = datetime.fromtimestamp(
                access_token_dict["expires_at"], tz=UTC
            )
        except KeyError:
            oauth_account.expires_at = None
        await oauth_account_repository.update(oauth_account)

    audit_logger(
        AuditLogMessage.OAUTH_PROVIDER_USER_ACCESS_TOKEN_GET,
        subject_user_id=user.id,
        oauth_provider_id=str(oauth_provider.id),
    )

    return oauth_account
