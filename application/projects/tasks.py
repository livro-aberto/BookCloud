import os
import git

from os.path import join
from shutil import copyfile

from celery import chain

from flask_babel import gettext as _

import application.branches

from application import app, ext, db
from application.users import User
from application.projects import Project, FileExists
from application.utils import write_file

from application.branches.tasks import build_branch

celery = ext.celery

@celery.task(bind=True)
def create_project(self, name, user_id):
    user = User.query.filter_by(id=user_id).one()

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

    message = 'Creating "{}" resource folders'.format(name)
    app.logger.info(message)
    self.update_state(state='PROGRESS', meta={'status': message})

    try:
        os.makedirs('/etc/seelekj')
    except:
        self.update_state(state='FAILURE', meta={'status': 'Could not do it'})
    os.makedirs(join('repos', name, '_resources'))
    os.makedirs(join('repos', name, '_resources/original'))
    os.makedirs(join('repos', name, '_resources/low_resolution'))
    os.makedirs(join('repos', name, '_resources/thumbnail'))
    # create the repository in the filesystem

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

    message = 'Project "{}" created'.format(name)
    app.logger.info(message)
    self.update_state(state='PROGRESS', meta={'status': message})

    db.session.add(project)
    db.session.commit()
    return new_branch.id


# Should be sent to branch
@celery.task(bind=True)
def new_file(self, project_id, filename):
    project = Project.query.filter_by(id=project_id).one()
    file_extension = '.rst'
    file_path = join(project.get_master().get_source_path(),
                     filename + file_extension)
    if os.path.isfile(file_path):
        raise FileExists
    else:
        stars = '*' * len(filename) + '\n'
        write_file(file_path, stars + filename + '\n' + stars)
        repo = project.get_master().get_repo()
        repo.index.add([filename + file_extension])
        project.get_master().build()
    app.logger.info('New file "{}" created'.format(filename))
