import os
import git

from os.path import join
from shutil import copyfile

from flask_babel import gettext as _

from application import app, ext, db
from application.users import User
from application.projects import Project
import application.branches

celery = ext.celery

@celery.task(bind=True)
def create_project(self, name, user_id):
    user = User.query.filter_by(id=user_id).one()

    from time import sleep

    sleep(1)
    message = 'Creating project "{}"...'.format(name)
    app.logger.info(message)
    self.update_state(state='PROGRESS', meta={'status': message})

    project = Project(name, user)
    # create the master branch
    new_branch = application.branches.Branch('master', project, None, user)
    db.session.add(new_branch)
    db.session.commit()
    # updating branch's self reference
    new_branch.origin_id = new_branch.id
    db.session.commit()
    # create folder for resources

    sleep(1)
    message = 'Creating "{}" resource folders'.format(name)
    app.logger.info(message)
    self.update_state(state='PROGRESS', meta={'status': message})

    os.makedirs(join('repos', name, '_resources'))
    os.makedirs(join('repos', name, '_resources/original'))
    os.makedirs(join('repos', name, '_resources/low_resolution'))
    os.makedirs(join('repos', name, '_resources/thumbnail'))
    # create the repository in the filesystem

    sleep(1)
    message = 'Creating "{}" repository'.format(name)
    app.logger.info(message)
    self.update_state(state='PROGRESS', meta={'status': message})

    repo_path = join('repos', name, 'master/source')
    os.makedirs(repo_path)
    os.symlink(os.path.abspath(join('repos', name, '_resources',
                                    'low_resolution')),
               os.path.abspath(join('repos', name,
                                    'master/source/_resources/')))
    git.Repo.init(repo_path)
    repo = git.Repo(repo_path)
    application.branches.config_repo(repo, user.username, user.email)
    copyfile('empty_repo/source/index.rst', join(repo_path, 'index.rst'))
    copyfile('empty_repo/.gitignore', join(repo_path, '.gitignore'))
    repo.index.add(['index.rst', '.gitignore'])
    author = git.Actor(user.username, user.email)
    repo.index.commit(_('Initial commit'), author=author)
    # build master
    new_branch.build(timeout=30)

    sleep(1)
    message = 'Project "{}" created'.format(name)
    app.logger.info(message)
    self.update_state(state='PROGRESS', meta={'status': message})

    sleep(1)
    db.session.add(project)
    db.session.commit()
    return project.id
