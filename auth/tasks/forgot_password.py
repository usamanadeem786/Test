import uuid

import dramatiq

from auth import schemas
from auth.services.email_template.contexts import ForgotPasswordContext
from auth.services.email_template.types import EmailTemplateType
from auth.tasks.base import TaskBase


class OnAfterForgotPasswordTask(TaskBase):
    __name__ = "on_after_forgot_password"

    async def run(self, user_id: str, reset_url: str):
        user = await self._get_user(uuid.UUID(user_id))
        tenant = await self._get_tenant(user.tenant_id)

        context = ForgotPasswordContext(
            tenant=schemas.tenant.Tenant.model_validate(tenant),
            user=schemas.user.UserEmailContext.model_validate(user),
            reset_url=reset_url,
        )

        async with self._get_email_subject_renderer() as email_subject_renderer:
            subject = await email_subject_renderer.render(
                EmailTemplateType.FORGOT_PASSWORD, context
            )

        async with self._get_email_template_renderer() as email_template_renderer:
            html = await email_template_renderer.render(
                EmailTemplateType.FORGOT_PASSWORD, context
            )

        self.email_provider.send_email(
            sender=tenant.get_email_sender(),
            recipient=(user.email, None),
            subject=subject,
            html=html,
        )


on_after_forgot_password = dramatiq.actor(OnAfterForgotPasswordTask())
