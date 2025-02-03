from fastapi import Depends

from auth.dependencies.logger import get_audit_logger
from auth.dependencies.repositories import get_repository
from auth.dependencies.tasks import get_send_task
from auth.dependencies.webhooks import TriggerWebhooks, get_trigger_webhooks
from auth.logger import AuditLogger
from auth.repositories import (
    RoleRepository,
    UserPermissionRepository,
    UserRoleRepository,
)
from auth.services.user_roles import UserRolesService
from auth.tasks import SendTask


async def get_user_roles_service(
    user_role_repository: UserRoleRepository = Depends(
        get_repository(UserRoleRepository)
    ),
    user_permission_repository: UserPermissionRepository = Depends(
        get_repository(UserPermissionRepository)
    ),
    role_repository: RoleRepository = Depends(get_repository(RoleRepository)),
    audit_logger: AuditLogger = Depends(get_audit_logger),
    send_task: SendTask = Depends(get_send_task),
    trigger_webhooks: TriggerWebhooks = Depends(get_trigger_webhooks),
) -> UserRolesService:
    return UserRolesService(
        user_role_repository,
        user_permission_repository,
        role_repository,
        audit_logger,
        trigger_webhooks,
        send_task,
    )
