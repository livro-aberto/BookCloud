from wtforms import Form
from application.utils import create_identifier

from flask_babel import gettext as _


class ProjectForm(Form):
    name = create_identifier(_('Project name'))

class FileForm(Form):
    name = create_identifier(_('File name'))

