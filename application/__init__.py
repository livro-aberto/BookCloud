from flask import Flask
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_migrate import Migrate
from flask_user import login_required, UserManager, UserMixin, SQLAlchemyAdapter, current_user

# limit number of visits
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import os

from flask_user import current_user

def get_identifier():
    if current_user.is_authenticated:
        return current_user.username
    return get_remote_address()

# Setup Flask app and app.config
app = Flask(__name__, instance_relative_config=True)

limiter = Limiter(
    app,
    key_func=get_identifier,
    global_limits=["200 per day", "50 per hour"])

# Initialize Flask-SQLAlchemy
db = SQLAlchemy(app)

# Setup Flask-Mail
mail = Mail()

from users import User

def create_app(extra_config_settings={}):
    """
    Initialize Flask applicaton
    """
    import application.views
    app.register_blueprint(application.views.bookcloud.bookcloud)
    app.register_blueprint(application.views.users.users)
    app.register_blueprint(application.views.projects.projects)
    app.register_blueprint(application.views.threads.threads)
    app.register_blueprint(application.views.branches.branches)
    # Configure app
    app.config.from_object('config')
    app.config.from_pyfile('instance_config.py')
    # Read extra config settings from extra arguments
    app.config.update(extra_config_settings)
    # Set languange
    app.config['LANGUAGE'] = 'pt_BR'
    if app.testing or app.config['TESTING']:
        # Disable CSRF checks while testing
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['LANGUAGE'] = 'en_US'
        app.config['BOOKCLOUD_URL_PREFIX'] = ''

    app.register_blueprint(application.views.temp,
                           url_prefix=app.config['BOOKCLOUD_URL_PREFIX'])

    # Setup Flask-Mail
    mail.init_app(app)

    # Setup Flask-User
    db_adapter = SQLAlchemyAdapter(db, User)        # Register the User model
    user_manager = UserManager(db_adapter, app)     # Initialize Flask-User

    return app



