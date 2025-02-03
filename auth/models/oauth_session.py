import secrets

from pydantic import UUID4
from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.sqltypes import String

from auth.models.base import Base
from auth.models.generics import GUID, CreatedUpdatedAt, ExpiresAt, UUIDModel
from auth.models.oauth_account import OAuthAccount
from auth.models.oauth_provider import OAuthProvider
from auth.models.tenant import Tenant
from auth.settings import settings


class OAuthSession(UUIDModel, CreatedUpdatedAt, ExpiresAt, Base):
    __tablename__ = "oauth_sessions"
    __lifetime_seconds__ = settings.oauth_session_lifetime_seconds

    token: Mapped[str] = mapped_column(
        String(length=255),
        default=secrets.token_urlsafe,
        nullable=False,
        index=True,
        unique=True,
    )
    redirect_uri: Mapped[str] = mapped_column(Text, nullable=False)

    oauth_provider_id: Mapped[UUID4] = mapped_column(
        GUID, ForeignKey(OAuthProvider.id, ondelete="CASCADE"), nullable=False
    )
    oauth_provider: Mapped[OAuthProvider] = relationship("OAuthProvider", lazy="joined")

    oauth_account_id: Mapped[UUID4 | None] = mapped_column(
        GUID, ForeignKey(OAuthAccount.id, ondelete="CASCADE"), nullable=True
    )
    oauth_account: Mapped[OAuthAccount | None] = relationship(
        "OAuthAccount", lazy="joined"
    )

    tenant_id: Mapped[UUID4] = mapped_column(
        GUID, ForeignKey(Tenant.id, ondelete="CASCADE"), nullable=False
    )
    tenant: Mapped[Tenant] = relationship("Tenant", lazy="joined")
