import functools
import json
import uuid

from auth_client import AuthTokenResponse, AuthUserInfo
from pydantic import UUID4
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from auth.models.base import Base
from auth.models.generics import CreatedUpdatedAt, UUIDModel


class AdminSessionToken(UUIDModel, CreatedUpdatedAt, Base):
    __tablename__ = "admin_session_tokens"

    token: Mapped[str] = mapped_column(String(length=255), unique=True, nullable=False)
    raw_tokens: Mapped[str] = mapped_column(Text, nullable=False)
    raw_userinfo: Mapped[str] = mapped_column(Text, nullable=False)

    def __repr__(self) -> str:
        return f"AdminSessionToken(id={self.id})"

    @functools.cached_property
    def tokens(self) -> AuthTokenResponse:
        return json.loads(self.raw_tokens)

    @functools.cached_property
    def userinfo(self) -> AuthUserInfo:
        return json.loads(self.raw_userinfo)

    @functools.cached_property
    def user_id(self) -> UUID4:
        return uuid.UUID(self.userinfo["sub"])
