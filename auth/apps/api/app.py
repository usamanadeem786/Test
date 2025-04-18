from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth import __version__
from auth.apps.api.routers.clients import router as clients_router
from auth.apps.api.routers.email_templates import router as email_templates_router
from auth.apps.api.routers.oauth_providers import router as oauth_providers_router
from auth.apps.api.routers.permissions import router as permissions_router
from auth.apps.api.routers.roles import router as roles_router
from auth.apps.api.routers.tenants import router as tenants_router
from auth.apps.api.routers.user_fields import router as user_fields_router
from auth.apps.api.routers.users import router as users_router
from auth.apps.api.routers.webhooks import router as webhooks_router
from auth.middlewares.security_headers import SecurityHeadersMiddleware
from auth.services.localhost import is_localhost
from auth.settings import settings

app = FastAPI(
    title="Auth Administration API",
    version=__version__,
    contact={
        "name": "Auth",
        "url": "https://docs.auth.dev",
        "email": "contact@auth.dev",
    },
    license_info={
        "name": "Elastic License 2.0 (ELv2)",
        "url": "https://github.com/auth-dev/auth/blob/main/LICENSE.md",
    },
    servers=[
        {
            "url": "{scheme}://{host}/admin/api",
            "variables": {
                "scheme": {
                    "enum": ["http", "https"],
                    "default": "http"
                    if is_localhost(settings.auth_domain)
                    else "https",
                },
                "host": {
                    "default": settings.auth_domain,
                    "description": "Your Auth server hostname",
                },
            },
        }
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=settings.allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(clients_router, prefix="/clients", tags=["Clients"])
app.include_router(
    email_templates_router, prefix="/email-templates", tags=["Email templates"]
)
app.include_router(
    oauth_providers_router, prefix="/oauth-providers", tags=["OAuth Providers"]
)
app.include_router(permissions_router, prefix="/permissions", tags=["Permissions"])
app.include_router(roles_router, prefix="/roles", tags=["Roles"])
app.include_router(tenants_router, prefix="/tenants", tags=["Tenants"])
app.include_router(users_router, prefix="/users", tags=["Users"])
app.include_router(user_fields_router, prefix="/user-fields", tags=["User fields"])
app.include_router(webhooks_router, prefix="/webhooks", tags=["Webhooks"])

__all__ = ["app"]
