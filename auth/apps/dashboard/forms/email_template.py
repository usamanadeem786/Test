from wtforms import StringField, TextAreaField

from auth.forms import CSRFBaseForm


class EmailTemplateUpdateForm(CSRFBaseForm):
    subject = StringField("Subject")
    content = TextAreaField("Content")
