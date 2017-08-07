from flask import Flask
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_migrate import Migrate
from flask_user import login_required, UserManager, UserMixin, SQLAlchemyAdapter, current_user

# limit number of visits
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_assets import Environment, Bundle

import os
from os.path import join
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

assets = Environment()

from users import User

def create_app(extra_config_settings={}):
    """
    Initialize Flask applicaton
    """

    # Setup Flask-Assets
    assets.init_app(app)
    with app.app_context():
        assets.load_path = [
            join(os.path.dirname(__file__), 'static/vendor/bower_components/'),
            join(os.path.dirname(__file__), 'static/')
        ]
    assets.register(
        'js_all',
        Bundle(
            #'klaus.js',
            'jquery/dist/jquery.min.js',
            Bundle('uikit/dist/js/uikit.min.js',
                   'uikit/dist/js/uikit-icons.min.js'
               ),
            'Jdenticon/dist/jdenticon.min.js',
            Bundle('jquery-textext/src/js/textext.core.js',
                   'jquery-textext/src/js/textext.plugin.tags.js',
                   'jquery-textext/src/js/textext.plugin.autocomplete.js',
                   'jquery-textext/src/js/textext.plugin.suggestions.js',
                   'jquery-textext/src/js/textext.plugin.filter.js',
                   'jquery-textext/src/js/textext.plugin.clear.js',
                   'jquery-textext/src/js/textext.plugin.focus.js',
                   'jquery-textext/src/js/textext.plugin.prompt.js',
                   'jquery-textext/src/js/textext.plugin.ajax.js',
                   'jquery-textext/src/js/textext.plugin.arrow.js'
               ),
            'google-diff-match-patch/diff_match_patch.js',
            output='js_all.js'
        ),
        filters='closure_js'
    )
    assets.register(
        'codemirror_js_all',
        Bundle(
            'codemirror/lib/codemirror.js',
               'codemirror/mode/rst/rst.js',
               'codemirror/mode/xml/xml.js',
               'codemirror/addon/mode/overlay.js',
               'codemirror/addon/search/search.js',
               'codemirror/addon/search/searchcursor.js',
               'codemirror/addon/dialog/dialog.js',
               'codemirror/addon/scroll/annotatescrollbar.js',
               'codemirror/addon/search/matchesonscrollbar.js',
               'codemirror/addon/search/jump-to-line.js',
               'codemirror/addon/merge/merge.js',
           ),
        output='codemirror_all.js',
        filters='closure_js'
    )
    assets.register(
        'css_all',
        Bundle(
            'uikit/dist/css/uikit.min.css',
            Bundle('jquery-textext/src/css/textext.core.css',
                   'jquery-textext/src/css/textext.plugin.tags.css',
                   'jquery-textext/src/css/textext.plugin.autocomplete.css',
                   'jquery-textext/src/css/textext.plugin.focus.css',
                   'jquery-textext/src/css/textext.plugin.prompt.css',
                   'jquery-textext/src/css/textext.plugin.clear.css',
                   'jquery-textext/src/css/textext.plugin.arrow.css'
               ),
            output='css_all.css'
        ),
        filters='cssmin'
    )
    assets.register(
        'codemirror_css_all',
        Bundle('codemirror/lib/codemirror.css',
               'codemirror/addon/merge/merge.css',
               'codemirror/addon/search/matchesonscrollbar.css'),
        output='codemirror_all.css',
        filters='cssmin'
    )

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



