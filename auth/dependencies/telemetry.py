from posthog import Posthog

from auth.services.posthog import posthog


async def get_posthog() -> Posthog:
    return posthog
