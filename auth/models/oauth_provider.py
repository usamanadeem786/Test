from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from auth.crypto.encryption import FernetEngine, StringEncryptedType
from auth.models.base import Base
from auth.models.generics import CreatedUpdatedAt, PydanticUrlString, UUIDModel
from auth.services.oauth_provider import AvailableOAuthProvider
from auth.settings import settings


class OAuthProvider(UUIDModel, CreatedUpdatedAt, Base):
    __tablename__ = "oauth_providers"

    provider: Mapped[AvailableOAuthProvider] = mapped_column(
        String(length=255), nullable=False
    )

    client_id: Mapped[str] = mapped_column(
        StringEncryptedType(Text, settings.encryption_key, FernetEngine), nullable=False
    )
    client_secret: Mapped[str] = mapped_column(
        StringEncryptedType(Text, settings.encryption_key, FernetEngine), nullable=False
    )
    scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    name: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    openid_configuration_endpoint: Mapped[str | None] = mapped_column(
        PydanticUrlString(Text), nullable=True
    )

    def get_provider_display_name(self) -> str:
        return AvailableOAuthProvider[self.provider].get_display_name()

    @property
    def display_name(self) -> str:
        return f"{self.get_provider_display_name()}{f' ({self.name})' if self.name else ''}"
