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
    origin = relationship('Branch', remote_side=id)
    collaborators = relationship('Branch')
    project = relationship('Project', back_populates='branches')

    def __init__(self, name, project, origin, owner):
        self.name = name
        self.project = project
        if origin:
            self.origin_id = origin.id
        self.owner_id = owner.id
        self.expires = True

    def get_source_path(self):
        return join('repos', self.project.name, self.name, 'source')

    def get_repo(self):
        return git.Repo(self.get_source_path())

    def get_git(self):
        return git.Repo(self.get_source_path()).git

    def is_dirty(self):
        repo_path = join('repos', self.project.name, self.name, 'source')
        return git.Repo(repo_path).is_dirty()

    def get_log(self):
        git_api = get_git(self.project.name, self.name)
        return git_api.log(
            '-15', '--no-merges', '--abbrev-commit','--decorate',
            '--full-history',
            "--format=format:%w(65,0,9)%an (%ar): %s %d", '--all')

# will be deprecated
def get_sub_branches(branch_obj):
    children = Branch.query.filter_by(origin_id=branch_obj.id)
    answer = { 'branch': branch_obj, 'subtree': [] }
    for child in children:
        if child.name != 'master':
            answer['subtree'].append(get_sub_branches(child))
    return answer

def get_branch_owner(project, branch):
    project_obj = application.projects.Project.query.filter_by(name=project).first()
    if project_obj:
        project_id = project_obj.id
        branch_obj = Branch.query.filter_by(project_id=project_id, name=branch).first()
        if branch_obj:
            return branch_obj.owner.username
    return None


def get_branch_origin(project, branch):
    project_id = application.projects.Project.query.filter_by(name=project).first().id
    origin_id = Branch.query.filter_by(project_id=project_id, name=branch).first().origin_id
    return Branch.query.filter_by(id=origin_id).first()

def clone_branch(project, origin, name, user):
    origin.expiration = None
    # create the branch on the database
    new_branch = Branch(name, project, origin, user)
    db.session.add(new_branch)
    db.session.commit()
    # clone repository from a certain origin branch
    branch_path = os.path.abspath(join(os.getcwd(), 'repos',
                                       project.name, name, 'source'))
    origin_repo = git.Repo(join('repos', project.name, origin.name, 'source'))
    origin_repo.clone(branch_path, branch=origin.name)
    branch_repo = git.Repo(branch_path)
    git_api = branch_repo.git
    git_api.checkout('HEAD', b=name)
    config_repo(branch_repo, user.username, user.email)
    # build the source
    build(project.name, name, timeout=30)

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



def build(project, branch, timeout=10):
    # Replace this terrible implementation
    config_path = 'conf'
    source_path = join('repos', project, branch, 'source')
    build_path = join('repos', project, branch, 'build/html')
    # args = ['-a', '-c conf']
    # if sphinx.build_main(args + ['source/', 'build/html/']):
    #     os.chdir(previous_wd)
    #     return False
    # os.chdir(previous_wd)
    # return True
    command = 'sphinx-build -c ' + config_path + ' ' + source_path + ' ' + build_path

    process = Command(command)
    process.run(timeout=timeout)
    #os.system(command)
    return True

def get_branch_by_name(project, branch):
    project_id = application.projects.Project.query.filter_by(name=project).first().id
    return Branch.query.filter_by(project_id=project_id, name=branch).first()


def update_branch(project, branch):
    # update from reviewer (if not master)
    project_obj = Project.get_by_name(project)
    if branch != 'master' and not project_obj.get_branch(branch).is_dirty():
        origin_branch = get_branch_origin(project, branch).name
        git_api = get_git(project, branch)
        git_api.fetch()
        git_api.merge('-s', 'recursive', '-Xours', 'origin/' + origin_branch)
        git_api.push('origin', branch)
    build(project, branch, timeout=20)

def update_subtree(project, branch):
    project_obj = Project.get_by_name(project)
    if not project_obj.get_branch(branch).is_dirty():
        update_branch(project, branch)
        project_id = application.projects.Project.query.filter_by(name=project).first().id
        branch_id = Branch.query.filter_by(project_id=project_id, name=branch).first().id
        children = Branch.query.filter_by(origin_id=branch_id)
        branch_obj = get_branch_by_name(project, branch)
        for child in children:
            if child.name != 'master':
                update_subtree(project, child.name)
        origin = get_branch_origin(project, branch).name
        origin_pendencies = get_requests(project, origin)
        if (branch == 'master' or children.first()
            or branch_obj.is_dirty() or not branch_obj.expires
            or branch in origin_pendencies):
            branch_obj.expiration = None
        else:
            current_time = datetime.utcnow()
            if branch_obj.expiration:
                if current_time > branch_obj.expiration:
                    # Delete branch
                    Branch.query.filter_by(id=branch_obj.id).delete()
                    db.session.commit()
                    branch_folder = join('repos', project, branch)
                    rmtree(branch_folder)
                    flash(_('Branch %s has been killed') % branch, 'info')
            else:
                flash(_('Branch %s has been marked obsolete') % branch, 'info')
                branch_obj.expiration = current_time + timedelta(days=1)
                db.session.commit()

def get_branch_origin(project, branch):
    project_id = application.projects.Project.query.filter_by(name=project).first().id
    origin_id = Branch.query.filter_by(project_id=project_id, name=branch).first().origin_id
    return Branch.query.filter_by(id=origin_id).first()

