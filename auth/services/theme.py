from auth.models import Theme
from auth.repositories import ThemeRepository


async def init_default_theme(repository: ThemeRepository):
    default_theme = await repository.get_default()
    if default_theme is None:
        await repository.create(Theme.build_default())
