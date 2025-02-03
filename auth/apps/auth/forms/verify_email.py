from wtforms import HiddenField, validators

from auth.forms import CSRFBaseForm
from auth.locale import gettext_lazy as _


class VerifyEmailForm(CSRFBaseForm):
    code = HiddenField(_("Verification code"), validators=[validators.InputRequired()])

    class Meta:
        id = "verify-email-form"
