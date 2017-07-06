from wtforms.widgets import html_params
from wtforms import (
    StringField, validators
)

def create_message(name):
    return StringField(name, [
        validators.Length(min=4, max=60),
        validators.Regexp('^[\w ,.?!-]+$',
                          message="Messages must contain only a-zA-Z0-9_-,.!? and space")])

def create_identifier(name):
    return StringField(name, [
        validators.Length(min=4, max=25),
        validators.Regexp(
            '^[\w-]+$',
            message="Identifiers must contain only a-zA-Z0-9_-"),])

def select_multi_checkbox(field, ul_class='', **kwargs):
    kwargs.setdefault('type', 'checkbox')
    field_id = kwargs.pop('id', field.id)
    html = [u'<ul style="list-style-type: none; padding-left: 0px;" %s>' % html_params(id=field_id, class_=ul_class)]
    for value, label, checked in field.iter_choices():
        choice_id = u'%s-%s' % (field_id, value)
        options = dict(kwargs, name=field.name, value=value, id=choice_id)
        if checked:
            options['checked'] = 'checked'
        html.append(u'<li><input style="margin-left: 0px;" %s /> ' % html_params(**options))
        html.append(u'<label for="%s">%s</label></li>' % (field_id, label))
    html.append(u'</ul>')
    return u''.join(html)

