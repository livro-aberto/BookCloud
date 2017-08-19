# Endpoints are converted to URLs using url_for()
# The empty endpoint ('') will be mapped to the root URL ('/')
USER_AFTER_CHANGE_PASSWORD_ENDPOINT      = 'bookcloud.home'
USER_AFTER_CHANGE_USERNAME_ENDPOINT      = 'bookcloud.home'
USER_AFTER_CONFIRM_ENDPOINT              = 'bookcloud.home'
USER_AFTER_FORGOT_PASSWORD_ENDPOINT      = 'bookcloud.home'
USER_AFTER_LOGIN_ENDPOINT                = 'bookcloud.home'
USER_AFTER_LOGOUT_ENDPOINT               = 'user.login'
USER_AFTER_REGISTER_ENDPOINT             = 'bookcloud.home'
USER_AFTER_RESEND_CONFIRM_EMAIL_ENDPOINT = 'bookcloud.home'
USER_AFTER_RESET_PASSWORD_ENDPOINT       = 'bookcloud.home'
USER_INVITE_ENDPOINT                     = 'bookcloud.home'

SQLALCHEMY_TRACK_MODIFICATIONS = False

