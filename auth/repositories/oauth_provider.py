from sqlalchemy import select

from auth.models import OAuthProvider
from auth.repositories.base import BaseRepository, UUIDRepositoryMixin


class OAuthProviderRepository(
    BaseRepository[OAuthProvider], UUIDRepositoryMixin[OAuthProvider]
):
    model = OAuthProvider

    async def all_by_name_and_provider(self) -> list[OAuthProvider]:
        return await self.list(
            select(OAuthProvider).order_by(OAuthProvider.name, OAuthProvider.provider)
        )
