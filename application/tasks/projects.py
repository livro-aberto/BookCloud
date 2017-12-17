from application import app, ext
from application.users import User
from application.projects import Project

celery = ext.celery

@celery.task()
def create_project(name, user_id):
    user = User.query.filter_by(id=user_id).one()
    project = Project(name, user)
    return project.id
