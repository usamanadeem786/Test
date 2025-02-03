from enum import StrEnum

from auth.services.email.base import (
    CreateDomainError,
    EmailDomain,
    EmailDomainDNSRecord,
    EmailError,
    EmailProvider,
    SendEmailError,
    VerifyDomainError,
)
from auth.services.email.null import Null
from auth.services.email.postmark import Postmark
from auth.services.email.sendgrid import Sendgrid
from auth.services.email.smtp import SMTP


class AvailableEmailProvider(StrEnum):
    NULL = "NULL"
    POSTMARK = "POSTMARK"
    SMTP = "SMTP"
    SENDGRID = "SENDGRID"


EMAIL_PROVIDERS: dict[AvailableEmailProvider, type[EmailProvider]] = {
    AvailableEmailProvider.NULL: Null,
    AvailableEmailProvider.POSTMARK: Postmark,
    AvailableEmailProvider.SMTP: SMTP,
    AvailableEmailProvider.SENDGRID: Sendgrid,
}

__all__ = [
    "AvailableEmailProvider",
    "EMAIL_PROVIDERS",
    "EmailError",
    "EmailProvider",
    "EmailDomain",
    "EmailDomainDNSRecord",
    "SendEmailError",
    "CreateDomainError",
    "VerifyDomainError",
]
