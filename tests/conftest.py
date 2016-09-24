# This file contains pytest 'fixtures'.
# If a test functions specifies the name of a fixture function as a parameter,
# the fixture function is called and its result is passed to the test function.
#
# Copyright 2014 SolidBuilds.com. All rights reserved
#
# Authors: Ling Thio <ling.thio@gmail.com>

import pytest

from application import create_app, db as the_db

the_app = create_app(dict(
    TESTING=True,  # Propagate exceptions
    LOGIN_DISABLED=False,  # Enable @register_required
    MAIL_SUPPRESS_SEND=True,  # Disable Flask-Mail send
    SERVER_NAME='localhost',  # Enable url_for() without request context
    SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',  # In-memory SQLite DB
    WTF_CSRF_ENABLED=False,  # Disable CSRF form validation
))

#import application.views as views
#views.set_lang('en_US')

def find_or_create_user(name, password):
    """ Find existing user or create new user """
    from application import User
    user = User.query.filter(User.username == name).first()
    if not user:
        user = User(username=name,
                    password=the_app.user_manager.hash_password(password),
                    active=True)
        the_db.session.add(user)
    return user

def create_users():
    """ Create users when app starts """

    # Create all tables
    the_db.create_all()

    # Add users
    user = find_or_create_user(u'foo', 'Foo123')
    user = find_or_create_user(u'bar', 'Bar123')

    # Save to DB
    the_db.session.commit()

create_users()

# Setup an application context (since the tests run outside of the webserver context)
the_app.app_context().push()


@pytest.fixture(scope='session')
def app():
    return the_app


@pytest.fixture(scope='session')
def db():
    """
    Initializes and returns a SQLAlchemy DB object
    """
    return the_db
