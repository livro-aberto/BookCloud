from application import create_app, ext
from celery.utils.log import get_task_logger

app = create_app()

celery = ext.celery

app.logger = get_task_logger(__name__)
