from application import create_app, ext
from celery.utils.log import get_task_logger

app = create_app({'API_ONLY': True})

celery = ext.celery

import application.projects


