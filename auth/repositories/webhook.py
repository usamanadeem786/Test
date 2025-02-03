from auth.models import Webhook
from auth.repositories.base import BaseRepository, UUIDRepositoryMixin


class WebhookRepository(BaseRepository[Webhook], UUIDRepositoryMixin[Webhook]):
    model = Webhook
