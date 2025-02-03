from auth.services.email import EmailProvider
from auth.settings import settings


async def get_email_provider() -> EmailProvider:
    return settings.get_email_provider()
