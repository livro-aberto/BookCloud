import os

# Flask settings
SECRET_KEY =              os.getenv('SECRET_KEY',       'THIS IS AN INSECURE SECRET')
SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL',     'mysql://username:password@localhost/db_name')
CSRF_ENABLED = True
SQLALCHEMY_TRACK_MODIFICATIONS = True

# Flask-Mail settings
USER_ENABLE_EMAIL =          False
USER_ENABLE_CONFIRM_EMAIL =  False
USER_SEND_REGISTERED_EMAIL = False
USER_ENABLE_LOGIN_WITHOUT_CONFIRM_EMAIL = False

# Endpoints are converted to URLs using url_for()
# The empty endpoint ('') will be mapped to the root URL ('/')
USER_AFTER_CHANGE_PASSWORD_ENDPOINT      = 'projects.home'
USER_AFTER_CHANGE_USERNAME_ENDPOINT      = 'projects.home'
USER_AFTER_CONFIRM_ENDPOINT              = 'projects.home'
USER_AFTER_FORGOT_PASSWORD_ENDPOINT      = 'projects.home'
USER_AFTER_LOGIN_ENDPOINT                = 'projects.home'
USER_AFTER_LOGOUT_ENDPOINT               = 'user.login'
USER_AFTER_REGISTER_ENDPOINT             = 'projects.home'
USER_AFTER_RESEND_CONFIRM_EMAIL_ENDPOINT = 'projects.home'
USER_AFTER_RESET_PASSWORD_ENDPOINT       = 'projects.home'
USER_INVITE_ENDPOINT                     = 'projects.home'

BOOKCLOUD_URL_PREFIX = '/'

MAIL_USERNAME =           os.getenv('MAIL_USERNAME',        'email@example.com')
MAIL_PASSWORD =           os.getenv('MAIL_PASSWORD',        'password')
MAIL_DEFAULT_SENDER =     os.getenv('MAIL_DEFAULT_SENDER',  '"MyApp" <noreply@example.com>')
MAIL_SERVER =             os.getenv('MAIL_SERVER',          'smtp.gmail.com')
MAIL_PORT =           int(os.getenv('MAIL_PORT',            '465'))
MAIL_USE_SSL =        int(os.getenv('MAIL_USE_SSL',         True))

ADMIN_MAIL = 'admin@domain.com'

# Flask-User settings
USER_APP_NAME        = "BookCloud"                # Used by email templates

LANGUAGES = {
    'en': 'English',
    'pt': 'Portugues'
}

USER_PROPERTIES = (
    { 'variable': 'integer_property_01',
      'type': 'integer',
      'title': 'State',
      'choices': ('NY', 'NE', 'CA') },
    { 'variable': 'boolean_property_01',
      'type': 'boolean',
      'title': 'Capital?' },
)
