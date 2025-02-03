from datetime import datetime

from pydantic import UUID4

from auth.schemas.generics import CreatedUpdatedAt, UUIDSchema
from auth.schemas.oauth_provider import OAuthProvider


class OAuthAccount(UUIDSchema, CreatedUpdatedAt):
    account_id: str
    oauth_provider_id: UUID4
    oauth_provider: OAuthProvider


class OAuthAccountAccessToken(UUIDSchema):
    account_id: str
    access_token: str
    expires_at: datetime | None = None
