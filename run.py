from application import create_app, db as the_db

import os

app = create_app(dict(
    TESTING=True,  # Propagate exceptions
    DEBUG=True,
    LOGIN_DISABLED=False,  # Enable @register_required
    MAIL_SUPPRESS_SEND=True,  # Disable Flask-Mail send
    WTF_CSRF_ENABLED=False,  # Disable CSRF form validation
    BOOKCLOUD_URL_PREFIX = ''
))

# Watch changes in template files
extra_dirs = ['application/templates',]
extra_files = extra_dirs[:]
for extra_dir in extra_dirs:
    for dirname, dirs, files in os.walk(extra_dir):
        for filename in files:
            filename = os.path.join(dirname, filename)
            if os.path.isfile(filename):
                extra_files.append(filename)

def find_or_create_user(name, email, password):
    """ Find existing user or create new user """
    from application import User
    user = User.query.filter(User.username == name).first()
    if not user:
        user = User(username=name,
                    password=app.user_manager.hash_password(password),
                    email=email,
                    active=True)
        the_db.session.add(user)
    return user

def create_users():
    """ Create users when app starts """

    # Create all tables
    #the_db.create_all()

    # Add users
    user = find_or_create_user(u'foo', 'foo@example.com', 'Foo123')
    user = find_or_create_user(u'bar', 'bar@example.com', 'Bar123')
    user = find_or_create_user(u'bla', 'bla@example.com', 'Bla123')

    # Save to DB
    the_db.session.commit()

create_users()

app.run(debug=True, extra_files=extra_files)
