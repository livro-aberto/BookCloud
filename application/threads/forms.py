from wtforms import (
    Form, StringField, validators,
    RadioField, SelectMultipleField, TextAreaField, SelectField
)

from ..utils import select_multi_checkbox

class ThreadForm(Form):
    title = StringField('Title', [ validators.Length(min=5, max=80)])
    flag = RadioField('Flag', choices = [('discussion', 'disucussion'),
                                         ('issue', 'issue')])
    usertags = SelectMultipleField('Users', widget=select_multi_checkbox)
    filetags = SelectMultipleField('Files', widget=select_multi_checkbox)
    namedtags = SelectMultipleField('Tags', widget=select_multi_checkbox)
    freetags = StringField('Hash Tags')

class NewThreadForm(ThreadForm):
    # Extends the thread form to include a first comment
    firstcomment = TextAreaField('Content', [ validators.Length(min=3, max=2000)])

class NewCommentForm(Form):
    comment = TextAreaField('Content', [ validators.Length(min=3, max=2000)])
