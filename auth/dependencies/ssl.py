import asyncio

from auth_client import AuthAsync
from uvicorn.server import Server

from auth.logger import logger
from auth.settings import settings


def _is_uvicorn_ssl() -> bool:
    """
    Hacky way to determine if the Uvicorn server is running with SSL,
    by retrieving the server instance from the running asyncio tasks.
    """
    try:
        for task in asyncio.all_tasks():
            coroutine = task.get_coro()
            if coroutine is not None:
                frame = coroutine.cr_frame
                if frame is not None:
                    args = frame.f_locals
                    if self := args.get("self"):
                        if isinstance(self, Server):
                            return self.config.is_ssl
    except RuntimeError:
        pass
    return False


_is_ssl = _is_uvicorn_ssl()
_scheme = "https" if _is_ssl else "http"
if _is_ssl:
    logger.debug("Uvicorn server is running with SSL")
else:
    logger.debug("Uvicorn server is running without SSL")

auth = AuthAsync(
    f"{_scheme}://localhost:{settings.port}",  # Always call Auth on localhost
    settings.auth_client_id,
    settings.auth_client_secret,
    encryption_key=settings.auth_encryption_key,
    host=settings.auth_domain,
    verify=False,
)


async def get_auth() -> AuthAsync:
    """
    This is Auth-ception.

    We are configuring a Auth client to authenticate Auth users to their account.
    """
    return auth
