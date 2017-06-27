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
app = Flask(__name__)
limiter = Limiter(
    app,
    key_func=get_identifier,
    global_limits=["200 per day", "50 per hour"]
)

# Initialize Flask-SQLAlchemy
db = SQLAlchemy(app)

# Setup Flask-Mail
mail = Mail(app)

# Define the User data model. Make sure to add flask.ext.user UserMixin !!!
class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    # User authentication information
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False, server_default='')
    reset_password_token = db.Column(db.String(100), nullable=False, server_default='')
    # User email information
    email = db.Column(db.String(255), nullable=False, unique=True)
    confirmed_at = db.Column(db.DateTime())
    # User information
    active = db.Column('is_active', db.Boolean(), nullable=False, server_default='0')
    first_name = db.Column(db.String(100), nullable=False, server_default='')
    last_name = db.Column(db.String(100), nullable=False, server_default='')
    # User profile information
    string_property_01 = db.Column(db.String(80), nullable=True, unique=False)
    string_property_02 = db.Column(db.String(80), nullable=True, unique=False)
    string_property_03 = db.Column(db.String(80), nullable=True, unique=False)
    string_property_04 = db.Column(db.String(80), nullable=True, unique=False)
    string_property_05 = db.Column(db.String(80), nullable=True, unique=False)
    integer_property_01 = db.Column(db.Integer, nullable=True, unique=False)
    integer_property_02 = db.Column(db.Integer, nullable=True, unique=False)
    integer_property_03 = db.Column(db.Integer, nullable=True, unique=False)
    integer_property_04 = db.Column(db.Integer, nullable=True, unique=False)
    integer_property_05 = db.Column(db.Integer, nullable=True, unique=False)
    integer_property_06 = db.Column(db.Integer, nullable=True, unique=False)
    integer_property_07 = db.Column(db.Integer, nullable=True, unique=False)
    integer_property_08 = db.Column(db.Integer, nullable=True, unique=False)
    integer_property_09 = db.Column(db.Integer, nullable=True, unique=False)
    integer_property_10 = db.Column(db.Integer, nullable=True, unique=False)
    boolean_property_01 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_02 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_03 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_04 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_05 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_06 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_07 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_08 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_09 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_10 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_11 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_12 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_13 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_14 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_15 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_16 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_17 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_18 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_19 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_20 = db.Column(db.Boolean(), nullable=True, unique=False)

class Project(db.Model):
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = relationship('User')
    branches = relationship('Branch', back_populates='project')

    def __init__(self, name, owner_id):
        self.name = name
        self.owner_id = owner_id

class Branch(db.Model):
    __tablename__ = 'branch'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    origin_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    expires = db.Column('expires', db.Boolean(), nullable=False)
    expiration =  db.Column(db.DateTime)

    owner = relationship('User')
    origin = relationship('Branch', remote_side=id)
    collaborators = relationship('Branch')
    project = relationship('Project', back_populates='branches')

    def __init__(self, name, project_id, origin_id, owner_id):
        self.name = name
        self.owner_id = owner_id
        self.origin_id = origin_id
        self.project_id = project_id
        self.expires = True

# Classes for comments

class Thread(db.Model):
    # One thread holds several comments and is associated to a project
    __tablename__ = 'thread'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Unicode(80), nullable=False, unique=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = relationship('User')
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    project = relationship('Project')
    flag = db.Column(db.String(10), nullable=False)
    posted_at = db.Column(db.DateTime(), nullable=False)

    def __init__(self, title, owner_id, project_id, flag, posted_at):
        self.title = title
        self.owner_id = owner_id
        self.project_id = project_id
        print(posted_at)
        self.posted_at = posted_at
        self.flag = flag

class Comment(db.Model):
    # Comments have a father thread and a lineage inside that thread.
    # The lineage encodes where in the thread tree that command appears
    __tablename__ = 'comment'
    id = db.Column(db.Integer, primary_key=True)
    lineage = db.Column(db.String(200))
    thread_id = db.Column(db.Integer, db.ForeignKey('thread.id'))
    thread = relationship('Thread')
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = relationship('User')
    content = db.Column(db.Unicode(2000), nullable=False, unique=False)
    posted_at = db.Column(db.DateTime(), nullable=False)

    def __init__(self, lineage, thread_id, owner_id, content, posted_at):
        self.lineage = lineage
        self.thread_id = thread_id
        self.owner_id = owner_id
        self.content = content
        self.posted_at = posted_at

class Likes(db.Model):
    # Associates a like to a comment
    __tablename__ = 'likes'
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'))
    comment = relationship('Comment')
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = relationship('User')

    def __init__(self, comment_id, owner_id):
        self.comment_id = comment_id
        self.owner_id = owner_id

class User_Tag(db.Model):
    # Associates a user to a thread
    __tablename__ = 'user_tag'
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('thread.id'))
    thread = relationship('Thread')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = relationship('User')

    def __init__(self, thread_id, user_id):
        self.thread_id = thread_id
        self.user_id = user_id

class File_Tag(db.Model):
    # Associates a file to a thread
    __tablename__ = 'file_tag'
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('thread.id'))
    thread = relationship('Thread')
    filename = db.Column(db.String(50), nullable=False, unique=False)

    def __init__(self, thread_id, filename):
        self.thread_id = thread_id
        self.filename = filename

class Named_Tag(db.Model):
    # Tags that are created by moderators
    __tablename__ = 'named_tag'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False, unique=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    project = relationship('Project')

    def __init__(self, name, project_id):
        self.name = name
        self.project_id = project_id

class Custom_Tag(db.Model):
    # Associates a named_tag to a thread
    __tablename__ = 'custom_tag'
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('thread.id'))
    thread = relationship('Thread')
    named_tag_id = db.Column(db.Integer, db.ForeignKey('named_tag.id'))
    named_tag = relationship('Named_Tag')

    def __init__(self, thread_id, named_tag_id):
        self.thread_id = thread_id
        self.named_tag_id = named_tag_id

class Free_Tag(db.Model):
    # Associates a free-named tag to a thread
    __tablename__ = 'free_tag'
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('thread.id'))
    thread = relationship('Thread')
    name = db.Column(db.String(20), nullable=False)

    def __init__(self, thread_id, name):
        self.thread_id = thread_id
        self.name = name




def create_app(extra_config_settings={}):
    """
    Initialize Flask applicaton
    """
    import application.views

    app.config.from_object('application.config')

    # Read extra config settings from function parameter 'extra_config_settings'
    app.config.update(extra_config_settings)  # Overwrite with 'extra_config_settings' parameter

    app.config['LANGUAGE'] = 'pt_BR'
    if app.testing or app.config['TESTING']:
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF checks while testing
        app.config['LANGUAGE'] = 'en_US'
        app.config['BOOKCLOUD_URL_PREFIX'] = ''

    app.register_blueprint(application.views.bookcloud,
                           url_prefix=app.config['BOOKCLOUD_URL_PREFIX'])

    # Setup Flask-Mail
    mail = Mail(app)

    # Create all database tables
    # db.create_all()

    # Setup Flask-User
    db_adapter = SQLAlchemyAdapter(db, User)        # Register the User model
    user_manager = UserManager(db_adapter, app)     # Initialize Flask-User

    return app



