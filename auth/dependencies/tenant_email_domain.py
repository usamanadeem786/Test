from fastapi import Depends

from auth.dependencies.email_provider import get_email_provider
from auth.dependencies.repositories import get_repository
from auth.repositories import EmailDomainRepository, TenantRepository
from auth.services.email import EmailProvider
from auth.services.tenant_email_domain import TenantEmailDomain
from auth.settings import settings


async def get_tenant_email_domain(
    tenant_repository: TenantRepository = Depends(TenantRepository),
    email_domain_repository: EmailDomainRepository = Depends(
        get_repository(EmailDomainRepository)
    ),
    email_provider: EmailProvider = Depends(get_email_provider),
) -> TenantEmailDomain:
    return TenantEmailDomain(
        email_provider,
        settings.email_provider,
        tenant_repository,
        email_domain_repository,
    )
