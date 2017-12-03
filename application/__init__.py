import os
from os.path import join
from flask_user import current_user
from celery import Celery

from flask import Flask
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_babel import Babel, gettext as _
from flask_user import login_required, UserManager, UserMixin, SQLAlchemyAdapter, current_user

# limit number of visits
from flask_limiter import Limiter
from flask_assets import Environment, Bundle

import utils

# Setup Flask app and app.config
app = Flask(__name__, instance_relative_config=True)

limiter = Limiter(
    app,
    key_func=utils.get_identifier,
    global_limits=["200 per day", "50 per hour"])

# Initialize Flask-SQLAlchemy
db = SQLAlchemy(app)

# Setup Flask-Mail
mail = Mail()

assets = Environment()

babel = Babel()

celery = Celery('app')

from users import User

def create_app(extra_config_settings={}):
    """
    Initialize Flask applicaton
    """

    # Setup Flask-Assets
    assets.init_app(app)
    # Configure app
    app.config.from_object('config')
    app.config.from_pyfile('instance_config.py')
    with app.app_context():
        assets.load_path = [
            join(os.path.dirname(__file__), 'static/vendor/bower_components/'),
            join(os.path.dirname(__file__), 'static/')
        ]
    assets.register(
        'js_all',
        Bundle(
            'klaus.js',
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
            'jquery.are-you-sure/jquery.are-you-sure.js',
            output='bundles/js_all.js'
        ),
        filters='rjsmin'
    )
    assets.register(
        'codemirror_js_all',
        Bundle('codemirror/lib/codemirror.js',
               'codemirror/mode/rst/rst.js',
               'codemirror/mode/xml/xml.js',
               'codemirror/addon/mode/overlay.js',
               'codemirror/addon/dialog/dialog.js',
               'codemirror/addon/search/searchcursor.js',
               'codemirror/addon/search/search.js',
               'codemirror/addon/scroll/annotatescrollbar.js',
               'codemirror/addon/search/matchesonscrollbar.js',
               'codemirror/addon/search/jump-to-line.js',
               'codemirror/addon/merge/merge.js',
           ),
        output='bundles/codemirror_all.js',
        filters='rjsmin'
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
            'uikit-style.css',
            output='bundles/css_all.css'
        ),
        filters='cssmin'
    )
    assets.register(
        'codemirror_css_all',
        Bundle('codemirror/lib/codemirror.css',
               'codemirror/addon/merge/merge.css',
               'codemirror/addon/dialog/dialog.css',
               'codemirror/addon/search/matchesonscrollbar.css'),
        output='bundles/codemirror_all.css',
        filters='cssmin'
    )

    import application.views
    import application.views.users
    import application.views.projects
    import application.views.threads
    import application.views.branches
    app.register_blueprint(application.views.users.users)
    app.register_blueprint(application.views.projects.projects)
    app.register_blueprint(application.views.threads.threads)
    app.register_blueprint(application.views.branches.branches)
    # Read extra config settings from extra arguments
    app.config.update(extra_config_settings)
    # Register template filters
    for (i, j) in [('force_unicode', utils.force_unicode),
          ('extract_author_name', utils.extract_author_name),
          ('formattimestamp', utils.formattimestamp),
          ('timesince', utils.timesince),
          ('rst2html', utils.rst2html)]:
        app.jinja_env.filters[i] = j
    # Set languange
    app.config['LANGUAGE'] = 'pt_BR'
    if app.testing or app.config['TESTING']:
        # Disable CSRF checks while testing
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['LANGUAGE'] = 'en_US'
        app.config['BOOKCLOUD_URL_PREFIX'] = ''

    #app.register_blueprint(application.views.temp,
    #                       url_prefix=app.config['BOOKCLOUD_URL_PREFIX'])

    # Setup Flask-Mail
    mail.init_app(app)
    # Setup babel
    babel.init_app(app)
    # Setup Celery
    celery.conf.add_defaults(app.config)
    # Setup Flask-User
    db_adapter = SQLAlchemyAdapter(db, User)        # Register the User model
    user_manager = UserManager(db_adapter, app)     # Initialize Flask-User

    return app



