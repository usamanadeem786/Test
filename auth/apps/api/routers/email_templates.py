import jinja2.exceptions
from fastapi import APIRouter, Depends, HTTPException, status

from auth import schemas
from auth.db import AsyncSession
from auth.dependencies.admin_authentication import is_authenticated_admin_api
from auth.dependencies.db import get_main_async_session
from auth.dependencies.email_template import (
    get_email_template_by_id_or_404,
    get_paginated_email_templates,
)
from auth.dependencies.logger import get_audit_logger
from auth.dependencies.pagination import PaginatedObjects
from auth.dependencies.repositories import get_repository
from auth.dependencies.webhooks import TriggerWebhooks, get_trigger_webhooks
from auth.errors import APIErrorCode
from auth.logger import AuditLogger
from auth.models import AuditLogMessage, EmailTemplate
from auth.repositories.email_template import EmailTemplateRepository
from auth.schemas.generics import PaginatedResults
from auth.services.email_template.contexts import EMAIL_TEMPLATE_CONTEXT_CLASS_MAP
from auth.services.email_template.renderers import (
    EmailSubjectRenderer,
    EmailTemplateRenderer,
)
from auth.services.email_template.types import EmailTemplateType
from auth.services.webhooks.models import EmailTemplateUpdated

router = APIRouter(dependencies=[Depends(is_authenticated_admin_api)])


@router.get(
    "/",
    name="email_templates:list",
    response_model=PaginatedResults[schemas.email_template.EmailTemplate],
)
async def list_email_templates(
    paginated_email_templates: PaginatedObjects[EmailTemplate] = Depends(
        get_paginated_email_templates
    ),
) -> PaginatedResults[schemas.email_template.EmailTemplate]:
    email_templates, count = paginated_email_templates
    return PaginatedResults(
        count=count,
        results=[
            schemas.email_template.EmailTemplate.model_validate(email_template)
            for email_template in email_templates
        ],
    )


@router.get(
    "/{id:uuid}",
    name="email_templates:get",
    response_model=schemas.email_template.EmailTemplate,
)
async def get_email_template(
    email_template: EmailTemplate = Depends(get_email_template_by_id_or_404),
) -> schemas.email_template.EmailTemplate:
    return schemas.email_template.EmailTemplate.model_validate(email_template)


@router.patch(
    "/{id:uuid}",
    name="email_templates:update",
    response_model=schemas.email_template.EmailTemplate,
)
async def update_email_template(
    email_template_update: schemas.email_template.EmailTemplateUpdate,
    email_template: EmailTemplate = Depends(get_email_template_by_id_or_404),
    repository: EmailTemplateRepository = Depends(
        get_repository(EmailTemplateRepository)
    ),
    session: AsyncSession = Depends(get_main_async_session),
    audit_logger: AuditLogger = Depends(get_audit_logger),
    trigger_webhooks: TriggerWebhooks = Depends(get_trigger_webhooks),
) -> schemas.email_template.EmailTemplate:
    email_template_update_dict = email_template_update.model_dump(exclude_unset=True)

    context_class = EMAIL_TEMPLATE_CONTEXT_CLASS_MAP[email_template.type]
    sample_context = await context_class.create_sample_context(session)

    email_template_preview = EmailTemplate(
        type=email_template.type,
        subject=email_template_update_dict.get("subject", email_template.subject),
        content=email_template_update_dict.get("content", email_template.content),
    )
    email_subject_renderer = EmailSubjectRenderer(
        repository, templates_overrides={email_template.type: email_template_preview}
    )
    email_template_renderer = EmailTemplateRenderer(
        repository, templates_overrides={email_template.type: email_template_preview}
    )
    try:
        await email_subject_renderer.render(
            EmailTemplateType[email_template_preview.type], sample_context
        )  # type: ignore
        await email_template_renderer.render(
            EmailTemplateType[email_template_preview.type], sample_context
        )  # type: ignore
    except jinja2.exceptions.TemplateError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=APIErrorCode.EMAIL_TEMPLATE_INVALID_TEMPLATE,
        ) from e

    for field, value in email_template_update_dict.items():
        setattr(email_template, field, value)

    await repository.update(email_template)
    audit_logger.log_object_write(AuditLogMessage.OBJECT_UPDATED, email_template)
    trigger_webhooks(
        EmailTemplateUpdated,
        email_template,
        schemas.email_template.EmailTemplate,
    )

    return schemas.email_template.EmailTemplate.model_validate(email_template)
