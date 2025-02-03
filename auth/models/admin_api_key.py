from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from auth.models.base import Base
from auth.models.generics import CreatedUpdatedAt, UUIDModel


class AdminAPIKey(UUIDModel, CreatedUpdatedAt, Base):
    __tablename__ = "admin_api_key"

    name: Mapped[str] = mapped_column(String(length=255), nullable=False)
    token: Mapped[str] = mapped_column(String(length=255), unique=True, nullable=False)
