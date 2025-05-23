from typing import Generic

from fastapi import Depends

from auth.db import AsyncSession
from auth.dependencies.db import get_main_async_session
from auth.repositories import get_repository as _get_repository
from auth.repositories.base import REPOSITORY


class get_repository(Generic[REPOSITORY]):
    def __init__(self, repository_class: type[REPOSITORY]):
        self.repository_class = repository_class

    async def __call__(
        self, session: AsyncSession = Depends(get_main_async_session)
    ) -> REPOSITORY:
        return _get_repository(self.repository_class, session)
