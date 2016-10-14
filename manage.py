from flask import Flask

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager

import application

app = application.create_app(dict(
    TESTING = True,
    SQLALCHEMY_DATABASE_URI = 'mysql://gutosurrex:w084jwgjhhq2mcmcsw@localhost/bookcloud',
))

db = application.db
migrate = Migrate(app, db)

manager = Manager(app)
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
