from sqlalchemy import select

from auth.models import EmailTemplate
from auth.repositories.base import BaseRepository, UUIDRepositoryMixin
from auth.services.email_template.types import EmailTemplateType


class EmailTemplateRepository(
    BaseRepository[EmailTemplate], UUIDRepositoryMixin[EmailTemplate]
):
    model = EmailTemplate

    async def get_by_type(self, type: EmailTemplateType) -> EmailTemplate | None:
        statement = select(EmailTemplate).where(EmailTemplate.type == type.value)
        return await self.get_one_or_none(statement)
