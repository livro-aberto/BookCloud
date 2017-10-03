from wtforms import Form, StringField, validators

from application.utils import create_identifier, create_message

from flask_babel import gettext as _

class CommitForm(Form):
    message = create_message(_('Message'))

class BranchForm(Form):
    name = create_identifier(_('Branch name'))





