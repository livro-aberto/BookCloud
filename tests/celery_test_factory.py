from application import create_app, ext
from celery.utils.log import get_task_logger
from flask import current_app
from celery import Celery

app = create_app(dict(
    API_ONLY=True,
    TESTING=True,  # Propagate exceptions
    LOGIN_DISABLED=False,  # Enable @register_required
    MAIL_SUPPRESS_SEND=False,  # Disable Flask-Mail send
    SERVER_NAME='localhost',  # Enable url_for() without request context
    SQLALCHEMY_DATABASE_URI='sqlite:////tmp/bookcloud_test.db',  # SQLite DB
    WTF_CSRF_ENABLED=False,  # Disable CSRF form validation
    CELERY_BROKER_URL = 'redis://localhost:6379/0',
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
    #CELERY_BROKER_TRANSPORT='redis://localhost:6379/0',
    #CELERY_TASK_ALWAYS_EAGER=True,
    #CELERY_CACHE_BACKEND='memory'
))


# def make_celery(app):
#     celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
#     celery.conf.update(app.config)
#     task_base = celery.Task

#     class ContextTask(task_base):
#         abstract = True

#         def __call__(self, *args, **kwargs):
#             if current_app.config['TESTING']:
#                 with app.test_request_context():
#                     return task_base.__call__(self, *args, **kwargs)
#             with app.app_context():
#                 return task_base.__call__(self, *args, **kwargs)

#     celery.Task = ContextTask
#     return celery

# celery = make_celery(app)

celery = ext.celery

import application.projects


