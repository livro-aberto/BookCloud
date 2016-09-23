import os
import application
import unittest
import tempfile

from flask import url_for

from random import choice
from string import ascii_uppercase


extra_config_settings = dict(
    TESTING=True,  # Propagate exceptions
    LOGIN_DISABLED=False,  # Enable @register_required
    MAIL_SUPPRESS_SEND=True,  # Disable Flask-Mail send
    SERVER_NAME='localhost',  # Enable url_for() without request context
    SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',  # In-memory SQLite DB
    WTF_CSRF_ENABLED=False,  # Disable CSRF form validation
)

application.app.config.update(extra_config_settings)


def create_users():
    """ Create users when app starts """

    # Create all tables
    application.db.create_all()

    # Add users
    user = find_or_create_user(u'foo', 'Foo123')
    user = find_or_create_user(u'bar', 'Bar123')

    # Save to DB
    application.db.session.commit()


def find_or_create_user(name, password):
    """ Find existing user or create new user """
    from application import User
    user = User.query.filter(User.username == name).first()
    if not user:
        user = User(username=name,
                    password=application.user_manager.hash_password(password))
        application.db.session.add(user)
    return user


class ApplicationTestCase(unittest.TestCase):

    def setUp(self):
        self.db_fd, application.app.config['DATABASE'] = tempfile.mkstemp()
        application.app.config['TESTING'] = True
        self.app = application.app.test_client()
        with application.app.app_context():
            application.db.create_all()
            create_users()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(application.app.config['DATABASE'])

    def test_home(self):
        rv = self.app.get('/')
        assert b'Projects list' in rv.data

    def test_redirection_login(self):
        rv = self.app.get('/login')
        assert b'You should be redirected automatically to target URL' in rv.data

    def test_view_login(self):
        rv = self.app.get('/user/sign-in')
        assert b'Sign in' in rv.data

    def login(self, username, password):
        return self.app.post('/user/sign-in', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.app.get('/logout', follow_redirects=True)

    def test_login(self):
        with application.app.app_context():
            rv = self.app.post(url_for('user.login'), data=dict(
                username='foo',
                password='Foo123'
            ), follow_redirects=True)
            print ">>>>"
            print rv.data
            print find_or_create_user('foo', 'Foo123').username
            print "<<<<"

            #rv = self.login('foo', 'Foo123')

    def test_view_new(self):
        a = self.login('foo', 'Foo123')
        rv = self.app.get('/new')
        assert 'Create new project' in rv.data

    def test_new(self):
        name = ''.join(choice(ascii_uppercase) for i in range(12))
        rv = self.app.post('/new', data=dict(
            project='Hello'
        ), follow_redirects=True)
        assert 'Project created successfuly!' in rv.data








if __name__ == '__main__':
    unittest.main()
