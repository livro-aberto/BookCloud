# Celery configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'


# Endpoints are converted to URLs using url_for()
# The empty endpoint ('') will be mapped to the root URL ('/')
USER_AFTER_CHANGE_PASSWORD_ENDPOINT      = 'home'
USER_AFTER_CHANGE_USERNAME_ENDPOINT      = 'home'
USER_AFTER_CONFIRM_ENDPOINT              = 'home'
USER_AFTER_FORGOT_PASSWORD_ENDPOINT      = 'home'
USER_AFTER_LOGIN_ENDPOINT                = 'home'
USER_AFTER_LOGOUT_ENDPOINT               = 'user.login'
USER_AFTER_REGISTER_ENDPOINT             = 'home'
USER_AFTER_RESEND_CONFIRM_EMAIL_ENDPOINT = 'home'
USER_AFTER_RESET_PASSWORD_ENDPOINT       = 'home'
USER_INVITE_ENDPOINT                     = 'home'

# Download limitations
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

SQLALCHEMY_TRACK_MODIFICATIONS = False

# Logging
LOGGING_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOGGING_LOCATION = 'log/BookCloud.log'
SPHINX_LOGGING_FOLDER = 'log/'
LOGGING_MAX_BYTES = 1024 * 1024
LOGGING_LEVEL = 'INFO'
