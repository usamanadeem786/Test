from pydantic import UUID4

from auth.schemas.generics import BaseModel, CreatedUpdatedAt
from auth.schemas.permission import PermissionEmbedded
from auth.schemas.role import RoleEmbedded


class UserPermissionCreate(BaseModel):
    id: UUID4


class BaseUserPermission(CreatedUpdatedAt):
    user_id: UUID4
    permission_id: UUID4
    from_role_id: UUID4 | None = None


class UserPermission(BaseUserPermission):
    permission: PermissionEmbedded
    from_role: RoleEmbedded | None
