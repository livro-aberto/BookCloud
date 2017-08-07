import os
import re
import json
from os.path import isfile, join
import string
import git

from datetime import datetime, timedelta

from flask import redirect, url_for, flash

from sqlalchemy.orm import relationship

from flask_babel import gettext as _

from application import db
import application.projects
from application.tools import Command, load_file
from application.users import User
from application.models import CRUDMixin

class Branch(CRUDMixin, db.Model):
    __tablename__ = 'branch'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    origin_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    expires = db.Column('expires', db.Boolean(), nullable=False)
    expiration =  db.Column(db.DateTime)

    owner = relationship('User')
    origin = relationship('Branch', remote_side=id, post_update=True)
    collaborators = relationship('Branch')
    project = relationship('Project', back_populates='branches')

    def __init__(self, name, project, origin, owner):
        self.name = name
        self.project = project
        if origin:
            self.origin_id = origin.id
        self.owner_id = owner.id
        self.expires = True

    def clone(self, name, user):
        """
        create a clone of self with a given name, owned by user
        """
        self.expiration = None
        # create the branch on the database
        new_branch = Branch(name, self.project, self, user)
        db.session.add(new_branch)
        db.session.commit()
        # clone repository in file system
        branch_path = os.path.abspath(join(os.getcwd(), 'repos',
                                           self.project.name,
                                           name, 'source'))
        self.get_repo().clone(branch_path, branch=self.name)
        branch_repo = git.Repo(branch_path)
        branch_repo.git.checkout('HEAD', b=name)
        config_repo(branch_repo, user.username, user.email)
        # build the source
        new_branch.build(timeout=30)
        return new_branch

    def get_source_path(self):
        return join('repos', self.project.name, self.name, 'source')

    def get_html_path(self):
        return join('repos', self.project.name, self.name, 'build/html')

    def get_repo(self):
        return git.Repo(self.get_source_path())

    def get_git(self):
        return git.Repo(self.get_source_path()).git

    def is_dirty(self):
        repo_path = join('repos', self.project.name, self.name, 'source')
        return git.Repo(repo_path).is_dirty()

    def get_log(self):
        git_api = self.get_git()
        return git_api.log(
            '-15', '--no-merges', '--abbrev-commit','--decorate',
            '--full-history',
            "--format=format:%w(65,0,9)%an (%ar): %s %d", '--all')

    def build(self, timeout=10):
        # Replace this terrible implementation
        config_path = 'conf'
        # args = ['-a', '-c conf']
        # if sphinx.build_main(args + ['source/', 'build/html/']):
        #     os.chdir(previous_wd)
        #     return False
        # os.chdir(previous_wd)
        # return True
        command = ('sphinx-build -c ' + config_path + ' '
                   + self.get_source_path() + ' '
                   + self.get_html_path())
        process = Command(command)
        process.run(timeout=timeout)
        return True

# will be deprecated
def get_sub_branches(branch):
    children = Branch.query.filter_by(origin_id=branch.id)
    answer = { 'branch': branch, 'subtree': [] }
    for child in children:
        if child.name != 'master':
            answer['subtree'].append(get_sub_branches(child))
    return answer

# will be deprecated
def get_git(project, branch):
    repo_path = join('repos', project, branch, 'source')
    repo = git.Repo(repo_path)
    return repo.git

# will be deprecated
def get_merging(project, branch):
    merge_file_path = join('repos', project, branch, 'merging.json')
    if isfile(merge_file_path):
        return json.loads(load_file(merge_file_path))

# will be deprecated
def get_requests(project, branch):
    git_api = get_git(project, branch)
    branches = string.split(git_api.branch())
    merged = string.split(git_api.branch('--merged'))
    unmerged = [item for item in branches if item not in merged]
    return unmerged

# will be deprecated
def get_merge_pendencies(project, branch):
    branch_repo_path = join('repos', project, branch)
    # user is merging?
    merging = get_merging(project, branch)
    if merging:
        return redirect(url_for('branches.merge', project=project,
                                branch=branch, other=merging['branch']))

def config_repo(repo, user_name, email):
    config = repo.config_writer()
    config.set_value('user', 'email', email)
    config.set_value('user', 'name', user_name)

def get_log_diff(project, origin, branch):
    git_api = get_git(project, origin)
    return git_api.log(origin + '..' + branch, '--graph',
                       '--abbrev-commit','--decorate', '--right-only',
                       "--format=format:%an (%ar): %s %d")


def build_latex(project, branch):
    # Replace this terrible implementation
    config_path = 'conf'
    source_path = join('repos', project, branch, 'source')
    build_path = join('repos', project, branch, 'build/latex')
    command = 'sphinx-build -a -b latex -c ' + config_path + ' ' + source_path + ' ' + build_path
    os.system(command)
    return True

def get_branch_by_name(project, branch):
    project_id = application.projects.Project.query.filter_by(name=project).first().id
    return Branch.query.filter_by(project_id=project_id, name=branch).first()

def update_branch(project, branch):
    # update from reviewer (if not master)
    if (branch.name != 'master'
        and not project.get_branch(branch.name).is_dirty()):
        git_api = branch.get_git()
        git_api.fetch()
        git_api.merge('-s', 'recursive', '-Xours', 'origin/'
                      + branch.origin.name)
        git_api.push('origin', branch.name)
    branch.build(timeout=20)

def update_subtree(project, branch):
    if not branch.is_dirty():
        update_branch(project, branch)
        children = Branch.query.filter_by(origin_id=branch.id)
        for child in children:
            if child.name != 'master':
                update_subtree(project, child)
        origin_pendencies = get_requests(project.name, branch.origin.name)
        if (branch.name == 'master' or children.first()
            or branch.is_dirty() or not branch.expires
            or branch.name in origin_pendencies):
            branch.expiration = None
        else:
            current_time = datetime.utcnow()
            if branch.expiration:
                if current_time > branch.expiration:
                    # Delete branch
                    Branch.query.filter_by(id=branch.id).delete()
                    db.session.commit()
                    branch_folder = join('repos', project.name, branch.name)
                    rmtree(branch_folder)
                    flash(_('Branch %s has been killed') % branch.name, 'info')
            else:
                branch.expiration = current_time + timedelta(days=1)
                db.session.commit()
                flash(_('Branch %s has been marked obsolete') % branch.name,
                      'info')

