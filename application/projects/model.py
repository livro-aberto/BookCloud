import re
import json
import os
from os.path import join
import git
from shutil import copyfile

from flask_babel import gettext as _



from os.path import isfile

from application import db
from sqlalchemy.orm import relationship

import application.branches
import application.users

from application.tools import load_file

from application.models import CRUDMixin

def get_labels(project):
    master_path = join('repos', project.name, 'master', 'source')
    label_list = []
    for f in os.listdir(master_path):
        if (isfile(join(master_path, f)) and f[0] != '.'):
            data = load_file(join(master_path, f))
            label_list.extend([splitext(f)[0] + '#' + l
                               for l in re.findall(r'^\.\. _([a-z\-]+):\s$', data, re.MULTILINE)])
    return json.dumps(label_list)

def create_project(project, user):
    # create a repository
    repo_path = join('repos', project, 'master/source')
    os.makedirs(repo_path)
    git.Repo.init(repo_path)
    repo = git.Repo(repo_path)
    application.branches.config_repo(repo, user.username, user.email)
    copyfile('empty_repo/source/index.rst', join(repo_path, 'index.rst'))
    copyfile('empty_repo/.gitignore', join(repo_path, '.gitignore'))
    repo.index.add(['index.rst', '.gitignore'])
    author = git.Actor(user.username, user.email)
    repo.index.commit(_('Initial commit'), author=author)
    # add project to database
    user_id = application.users.User.query.filter(
        application.users.User.username == user.username).first().id
    new_project = Project(project, user_id)
    db.session.add(new_project)
    # add master branch to database
    db.session.commit()
    project_id = Project.query.filter_by(name=project).first().id
    origin_id = 1
    new_branch = application.branches.Branch('master', project_id, origin_id, user_id)
    db.session.add(new_branch)
    db.session.commit()
    # updating branch's self reference
    new_branch = application.branches.Branch.query.filter_by(project_id=project_id).first()
    new_branch.origin_id = new_branch.id
    db.session.commit()
    application.branches.build(project, 'master')




class Project(CRUDMixin, db.Model):
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = relationship('User')
    branches = relationship('Branch', back_populates='project')

    def __init__(self, name, owner_id):
        self.name = name
        self.owner_id = owner_id
