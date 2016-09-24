from flask import Flask
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_migrate import Migrate
from flask_user import login_required, UserManager, UserMixin, SQLAlchemyAdapter, current_user

import os

# Setup Flask app and app.config
app = Flask(__name__)

def create_app(extra_config_settings={}):
    """
    Initialize Flask applicaton
    """

    app.config.from_object('config')

    # Read extra config settings from function parameter 'extra_config_settings'
    print(extra_config_settings)
    app.config.update(extra_config_settings)  # Overwrite with 'extra_config_settings' parameter
    print(app.config['TESTING'])


    if app.testing or app.config['TESTING']:
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF checks while testing
        app.config['LANGUAGE'] = 'en_US'

    # Setup Flask-Mail
    mail = Mail(app)

    return app

create_app()

# Initialize Flask extensions
db = SQLAlchemy(app)                            # Initialize Flask-SQLAlchemy
migrate = Migrate(app, db)                      # Initialize Flask-Migrate
mail = Mail(app)                                # Initialize Flask-Mail

# Define the User data model. Make sure to add flask.ext.user UserMixin !!!
class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    # User authentication information
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False, server_default='')
    reset_password_token = db.Column(db.String(100), nullable=False, server_default='')
    # User email information
    # email = db.Column(db.String(255), nullable=False, unique=True)
    # confirmed_at = db.Column(db.DateTime())
    # User information
    active = db.Column('is_active', db.Boolean(), nullable=False, server_default='0')
    first_name = db.Column(db.String(100), nullable=False, server_default='')
    last_name = db.Column(db.String(100), nullable=False, server_default='')

class Project(db.Model):
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = db.relationship('User')

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
    owner = db.relationship('User')
    origin = db.relationship('Branch')
    project = db.relationship('Project')

    def __init__(self, name, project_id, origin_id, owner_id):
        self.name = name
        self.owner_id = owner_id
        self.origin_id = origin_id
        self.project_id = project_id


# Create all database tables
db.create_all()

# Setup Flask-User
db_adapter = SQLAlchemyAdapter(db, User)        # Register the User model
user_manager = UserManager(db_adapter, app)     # Initialize Flask-User

import application.views
