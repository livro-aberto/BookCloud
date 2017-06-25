from wtforms import Form, StringField, validators

class ProjectForm(Form):
    name = StringField('Identifier', [
        validators.Length(min=4, max=25),
        validators.Regexp(
            '^[\w-]+$',
            message="Identifiers must contain only a-zA-Z0-9_-"),])



