from wtforms import StringField, validators

from auth.forms import CSRFBaseForm


class APIKeyCreateForm(CSRFBaseForm):
    name = StringField("Name", validators=[validators.InputRequired()])
