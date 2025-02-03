from sqlalchemy import select

from auth.models import AuditLog
from auth.repositories.base import BaseRepository, UUIDRepositoryMixin


class AuditLogRepository(BaseRepository[AuditLog], UUIDRepositoryMixin[AuditLog]):
    model = AuditLog

    async def get_latest(self) -> AuditLog | None:
        statement = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(1)
        return await self.get_one_or_none(statement)
