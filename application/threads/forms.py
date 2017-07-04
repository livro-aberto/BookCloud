from wtforms import (
    Form, StringField, validators, RadioField,
    TextAreaField, SelectField, Field
)
from wtforms.widgets.core import HTMLString, html_params, escape

from application.utils import create_message

import json
import re

def clean_string(s):
    """ Turn a string into a valid identifier """
    # Remove invalid characters
    s = re.sub('[^0-9a-zA-Z_]', '', s)
    # Remove leading characters until we find a letter or underscore
    s = re.sub('^[^a-zA-Z_]+', '', s)
    return s

class TextExtWidget(object):
    def __init__(self, choices):
        self.choices = choices

    def __call__(self, field, **kwargs):
        # Allow passing title= or alternately use field.description
        title = kwargs.pop('title', field.label.text or '')
        params = html_params(title=title, id=field.name, **kwargs)
        html = ('<textarea %s class="example"\n'
                '     rows="1" cols="80" name="%s"\n'
                '     placeholder="..."></textarea>\n') % (params, field.name)
        if self.choices == '[]':
            script_params = ('      plugins : "tags",\n'
                             '      tagsItems: %s,\n') % json.dumps(field.data)
        else:
            script_params = (
                '      tagsItems: %s,\n'
                '      plugins : "autocomplete suggestions filter tags",\n'
                '      filterItems: %s,\n'
                '      suggestions: %s,\n') % (json.dumps(field.data),
                                               self.choices, self.choices)
        script = ('     <script type="text/javascript">\n'
                  '       $("#%s")\n'
                  '       .textext({\n'
                  '%s'
                  '       });\n'
                  '     </script>') % (field.name, script_params)
        return HTMLString(html + script)

class TextExtField(Field):
    def __init__(self, label='', validators=None, choices='[]', **kwargs):
        super(TextExtField, self).__init__(label, validators, **kwargs)
        self.widget = TextExtWidget(choices)

    def _value(self):
        if self.data:
            return u', '.join(self.data[0])
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = [x.strip() for x in json.loads(valuelist[0])]
        else:
            self.data = []

class ThreadForm(Form):
    title = create_message('Title')
    flag = RadioField('Flag', default='discussion',
                      choices=[('discussion', 'disucussion'),
                               ('issue', 'issue')])
    user_tags = TextExtField('Users')
    file_tags = TextExtField('Files')
    custom_tags = TextExtField('Tags')
    free_tags = TextExtField('Hash Tags')


class NewThreadForm(ThreadForm):
    # Extends the thread form to include a first comment
    firstcomment = TextAreaField('Content',
                                 [validators.Length(min=3, max=2000)])

class CommentForm(Form):
    comment = TextAreaField('Content', [ validators.Length(min=3, max=2000)])

class CommentSearchForm(Form):
    search = StringField('Search', [ validators.Length(min=3, max=60)])
