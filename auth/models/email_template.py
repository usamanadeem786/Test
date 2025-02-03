from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from auth.models.base import Base
from auth.models.generics import CreatedUpdatedAt, UUIDModel
from auth.services.email_template.types import EmailTemplateType


class EmailTemplate(UUIDModel, CreatedUpdatedAt, Base):
    __tablename__ = "email_templates"

    type: Mapped[EmailTemplateType] = mapped_column(
        String(length=255), nullable=False, unique=True
    )
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    def get_type_display_name(self) -> str:
        return EmailTemplateType[self.type].get_display_name()
