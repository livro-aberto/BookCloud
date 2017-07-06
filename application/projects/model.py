import re
import json
import git
import os
from os.path import join, isfile, splitext
from shutil import copyfile

from flask_babel import gettext as _
from sqlalchemy.orm import relationship

from application import db
import application.branches
import application.users
from application.tools import load_file
from application.models import CRUDMixin

class Project(CRUDMixin, db.Model):
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = relationship('User')
    branches = relationship('Branch', back_populates='project')

    def get_labels(self):
        master_path = join('repos', self.name, 'master', 'source')
        label_list = []
        for f in os.listdir(master_path):
            if (isfile(join(master_path, f)) and f[0] != '.'):
                data = load_file(join(master_path, f))
                label_list.extend(
                    [splitext(f)[0] + '#' + l for l in
                     re.findall(r'^\.\. _([a-z\-]+):\s$', data, re.MULTILINE)])
        return json.dumps(label_list)

    def __init__(self, name, user):
        self.name = name
        self.owner_id = user.id
        # create the master branch
        new_branch = application.branches.Branch('master', self, None, user)
        db.session.add(new_branch)
        db.session.commit()
        # updating branch's self reference
        new_branch.origin_id = new_branch.id
        db.session.commit()
        # create the repository in the filesystem
        repo_path = join('repos', name, 'master/source')
        os.makedirs(repo_path)
        git.Repo.init(repo_path)
        repo = git.Repo(repo_path)
        application.branches.config_repo(repo, user.username, user.email)
        copyfile('empty_repo/source/index.rst', join(repo_path, 'index.rst'))
        copyfile('empty_repo/.gitignore', join(repo_path, '.gitignore'))
        repo.index.add(['index.rst', '.gitignore'])
        author = git.Actor(user.username, user.email)
        repo.index.commit(_('Initial commit'), author=author)
        application.branches.build(name, 'master')
