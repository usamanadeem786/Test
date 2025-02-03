from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyCookie
from auth_client import AuthUserInfo

from auth.crypto.token import get_token_hash
from auth.dependencies.repositories import get_repository
from auth.models import AdminSessionToken
from auth.repositories import AdminSessionTokenRepository
from auth.settings import settings

cookie_scheme = APIKeyCookie(
    name=settings.auth_admin_session_cookie_name, auto_error=False
)


async def get_optional_admin_session_token(
    token: str | None = Depends(cookie_scheme),
    repository: AdminSessionTokenRepository = Depends(
        get_repository(AdminSessionTokenRepository)
    ),
) -> AdminSessionToken | None:
    if token is None:
        return None
    token_hash = get_token_hash(token)
    session_token = await repository.get_by_token(token_hash)
    return session_token


async def get_admin_session_token(
    request: Request,
    admin_session_token: AdminSessionToken | None = Depends(
        get_optional_admin_session_token
    ),
) -> AdminSessionToken:
    if admin_session_token is None:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": str(request.url_for("dashboard.auth:login"))},
        )
    return admin_session_token


async def get_userinfo(
    session_token: AdminSessionToken = Depends(get_admin_session_token),
) -> AuthUserInfo:
    return session_token.userinfo
