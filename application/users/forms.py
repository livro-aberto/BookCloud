from flask_babel import gettext as _
from wtforms import Form, SelectMultipleField

class SubscriptionForm(Form):
    subscriptions = SelectMultipleField('Subscriptions', choices=[])
