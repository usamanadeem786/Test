from fastapi import Cookie, Depends

from auth.dependencies.repositories import get_repository
from auth.dependencies.tenant import get_current_tenant
from auth.dependencies.user_field import get_user_create_model, get_user_fields
from auth.dependencies.users import get_user_manager
from auth.models import RegistrationSession, Tenant, UserField
from auth.repositories import OAuthAccountRepository, RegistrationSessionRepository
from auth.schemas.user import UF, UserCreate
from auth.services.registration_flow import RegistrationFlow
from auth.services.user_manager import UserManager
from auth.settings import settings


async def get_registration_flow(
    registration_session_repository: RegistrationSessionRepository = Depends(
        get_repository(RegistrationSessionRepository)
    ),
    oauth_account_repository: OAuthAccountRepository = Depends(
        get_repository(OAuthAccountRepository)
    ),
    user_manager: UserManager = Depends(get_user_manager),
    user_create_model: type[UserCreate[UF]] = Depends(get_user_create_model),
    user_fields: list[UserField] = Depends(get_user_fields),
) -> RegistrationFlow:
    return RegistrationFlow(
        registration_session_repository,
        oauth_account_repository,
        user_manager,
        user_create_model,
        user_fields,
    )


async def get_optional_registration_session(
    token: str | None = Cookie(None, alias=settings.registration_session_cookie_name),
    registration_session_repository: RegistrationSessionRepository = Depends(
        get_repository(RegistrationSessionRepository)
    ),
    tenant: Tenant = Depends(get_current_tenant),
) -> RegistrationSession | None:
    if token is None:
        return None

    registration_session = await registration_session_repository.get_by_token(token)
    if registration_session is None:
        return None

    if registration_session.tenant_id != tenant.id:
        return None

    return registration_session
