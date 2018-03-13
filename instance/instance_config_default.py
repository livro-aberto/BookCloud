import os

# Flask settings
SECRET_KEY = 'THIS IS AN INSECURE SECRET'
SQLALCHEMY_DATABASE_URI = ('mysql://user:pass'
                           '@localhost/bookcloud')
CSRF_ENABLED = True

# Flask-Mail settings
USER_ENABLE_EMAIL =          False
USER_ENABLE_CONFIRM_EMAIL =  False
USER_SEND_REGISTERED_EMAIL = False
USER_ENABLE_LOGIN_WITHOUT_CONFIRM_EMAIL = False

BOOKCLOUD_URL_PREFIX = '/'

MAIL_USERNAME = 'email@example.com'
MAIL_PASSWORD = 'password'
MAIL_DEFAULT_SENDER = '"MyApp" <noreply@example.com>'
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 465
MAIL_USE_SSL = int(True)

ADMIN_MAIL = 'mail@example.com'

CONFIG_PATH = 'classes/basic'

# Flask-User settings
USER_APP_NAME = "BookCloud"       # Used by email templates

USER_PROPERTIES = (
    { 'variable': 'integer_property_01',
      'type': 'integer',
      'title': 'State',
      'choices': ('NY', 'NE', 'CA') },
    { 'variable': 'boolean_property_01',
      'type': 'boolean',
      'title': 'Capital?' },
)
