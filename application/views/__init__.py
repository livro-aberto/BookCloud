import os
import re
import math
import json
from os.path import isdir, isfile, join, splitext
import flask
import urllib
from flask import render_template, render_template_string, request
from flask import redirect, url_for, Response, flash, Blueprint
from flask_user import login_required, SQLAlchemyAdapter, current_user
from sqlalchemy import or_, desc
from application import app, db, User, Project, Branch, Thread, Comment, File_Tag, Named_Tag, Free_Tag, limiter, mail
import string
from shutil import copyfile, rmtree
import git
from difflib import HtmlDiff
import traceback
from datetime import datetime, timedelta

from flask_babel import Babel, gettext as _

from flask_mail import Mail, Message

from wtforms import Form, BooleanField, StringField, validators,\
    RadioField, SelectMultipleField, TextAreaField, SelectField, HiddenField

from wtforms.widgets import html_params

# for identicon hashs
import hashlib

import sphinx

from creole import html2rest

from application.threads import (
    NewThreadForm,
    ThreadForm, NewCommentForm
)

# import special tools for this platform
from application.tools import window, rst2html, Command, get_git, load_file,\
    write_file, get_merging, get_requests, get_merge_pendencies,\
    config_repo, is_dirty, get_log, get_log_diff, last_modified

mail.init_app(app)

config_path = 'conf'

bookcloud = Blueprint('bookcloud', __name__, template_folder='templates')

babel = Babel(app)

import pprint
pp = pprint.PrettyPrinter(indent=4).pprint

class IdentifierForm(Form):
    name = StringField('Identifier', [
        validators.Length(min=4, max=25),
        validators.Regexp('^[\w-]+$', message="Identifiers must contain only a-zA-Z0-9_-"),
    ])

class MessageForm(Form):
    message = StringField('Message', [
        validators.Length(min=4, max=60),
        validators.Regexp('^[\w ,.?!-]+$',
                          message="Messages must contain only a-zA-Z0-9_-,.!? and space"),
    ])

from ..utils import get_branch_owner, menu_bar, select_multi_checkbox

@babel.localeselector
def get_locale():
    # if a user is logged in, use the locale from the user settings
    # user = getattr(g, 'user', None)
    # if user is not None:
    #     return user.locale
    #print(request.accept_languages.best_match(app.config['LANGUAGES'].keys()))
    #return request.accept_languages.best_match(app.config['LANGUAGES'].keys())
    return 'en'

def update_branch(project, branch):
    # update from reviewer (if not master)
    if branch != 'master' and not is_dirty(project, branch):
        origin_branch = get_branch_origin(project, branch).name
        git_api = get_git(project, branch)
        git_api.fetch()
        git_api.merge('-s', 'recursive', '-Xours', 'origin/' + origin_branch)
        git_api.push('origin', branch)
    build(project, branch, timeout=20)

def update_subtree(project, branch):
    if not is_dirty(project, branch):
        update_branch(project, branch)
        project_id = Project.query.filter_by(name=project).first().id
        branch_id = Branch.query.filter_by(project_id=project_id, name=branch).first().id
        children = Branch.query.filter_by(origin_id=branch_id)
        branch_obj = get_branch_by_name(project, branch)
        for child in children:
            if child.name != 'master':
                update_subtree(project, child.name)
        origin = get_branch_origin(project, branch).name
        origin_pendencies = get_requests(project, origin)
        if (branch == 'master' or children.first()
            or is_dirty(project, branch) or not branch_obj.expires
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

@app.before_request
def before_request():
    flask.g.locale = get_locale()

def get_branch_by_name(project, branch):
    project_id = Project.query.filter_by(name=project).first().id
    return Branch.query.filter_by(project_id=project_id, name=branch).first()


@app.context_processor

#def listat(obj):
#    return obj.__dict__

def package():
    sent_package = {}
    if 'project' in request.view_args:
        project = request.view_args['project']
        sent_package['project'] = project
        sent_package['project_owner'] = get_branch_owner(project, 'master')
        if 'branch' in request.view_args:
            branch = request.view_args['branch']
            if current_user.is_authenticated:
                if current_user.username == get_branch_owner(project, branch):
                    branch_obj = get_branch_by_name(request.view_args['project'],
                                                    request.view_args['branch'])
                    branch_obj.expiration = None
            sent_package['branch'] = branch
            db.session.commit()
    sent_package['is_dirty'] = is_dirty
    sent_package['get_requests'] = get_requests
    def has_requests(project, branch):
        return len(get_requests(project, branch)) > 0
    sent_package['has_requests'] = has_requests
    sent_package['get_log_diff'] = get_log_diff
    sent_package['last_modified'] = last_modified
    sent_package['get_branch_by_name'] = get_branch_by_name
    sent_package['hash'] = lambda x: hashlib.sha256(x).hexdigest()
    sent_package['_'] = _
    sent_package['url_encode'] = lambda x: urllib.quote(x, safe='')
    sent_package['current_user'] = current_user
    sent_package['floor'] = math.floor
    sent_package['len'] = len
    sent_package['getattr'] = getattr
    #sent_package['listat'] = listat
    return sent_package

def create_project(project, user):
    # create a repository
    repo_path = join('repos', project, 'master/source')
    os.makedirs(repo_path)
    git.Repo.init(repo_path)
    repo = git.Repo(repo_path)
    config_repo(repo, user.username, user.email)
    copyfile('empty_repo/source/index.rst', join(repo_path, 'index.rst'))
    copyfile('empty_repo/.gitignore', join(repo_path, '.gitignore'))
    repo.index.add(['index.rst', '.gitignore'])
    author = git.Actor(user.username, user.email)
    repo.index.commit(_('Initial commit'), author=author)
    # add project to database
    user_id = User.query.filter(User.username == user.username).first().id
    new_project = Project(project, user_id)
    db.session.add(new_project)
    # add master branch to database
    db.session.commit()
    project_id = Project.query.filter_by(name=project).first().id
    origin_id = 1
    new_branch = Branch('master', project_id, origin_id, user_id)
    db.session.add(new_branch)
    db.session.commit()
    # updating branch's self reference
    new_branch = Branch.query.filter_by(project_id=project_id).first()
    new_branch.origin_id = new_branch.id
    db.session.commit()
    build(project, 'master')

def get_sub_branches(branch_obj):
    children = Branch.query.filter_by(origin_id=branch_obj.id)
    answer = { 'branch': branch_obj, 'subtree': [] }
    for child in children:
        if child.name != 'master':
            answer['subtree'].append(get_sub_branches(child))
    return answer

def get_branch_origin(project, branch):
    project_id = Project.query.filter_by(name=project).first().id
    origin_id = Branch.query.filter_by(project_id=project_id, name=branch).first().origin_id
    return Branch.query.filter_by(id=origin_id).first()

def create_branch(project, origin, branch, user_name):
    # Clone repository from a certain origin branch
    branch_path = join('repos', project, branch, 'source')
    origin_repo = git.Repo(join('repos', project, origin, 'source'))
    origin_repo.clone(os.path.abspath(join(os.getcwd(), branch_path)), branch=origin)
    branch_repo = git.Repo(os.path.abspath(join(os.getcwd(), branch_path)))
    config_repo(branch_repo, user_name, user_name + '@here.com')
    git_api = branch_repo.git
    git_api.checkout('HEAD', b=branch)

    project_id = Project.query.filter_by(name=project).first().id
    origin_obj = Branch.query.filter_by(project_id=project_id, name=origin).first()
    origin_obj.expiration = None
    owner_id = User.query.filter_by(username=user_name).first().id
    new_branch = Branch(branch, project_id, origin_obj.id, owner_id)

    db.session.add(new_branch)
    db.session.commit()
    build(project, branch, timeout=30)

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

def build_latex(project, branch):
    # Replace this terrible implementation
    config_path = 'conf'
    source_path = join('repos', project, branch, 'source')
    build_path = join('repos', project, branch, 'build/latex')
    command = 'sphinx-build -a -b latex -c ' + config_path + ' ' + source_path + ' ' + build_path
    os.system(command)
    return True

import application.users as users
from .users import users

app.register_blueprint(users)


@limiter.exempt
@bookcloud.route('/')
def home():
    path = 'repos'
    projects = [d.name for d in Project.query.all()]
    project_folders = [d for d in os.listdir(path) if isdir(join(path, d))]
    projects_without_folder = set(projects) - set(project_folders)
    if projects_without_folder:
        flash('Some projects have no folder (%s)' % ', '.join(projects_without_folder),
              'error')
    folders_without_project = set(project_folders) - set(projects)
    if folders_without_project:
        flash('Some folders have no project (%s)' % ', '.join(folders_without_project),
              'error')
    projects = list(set(projects) - set(projects_without_folder))
    menu = menu_bar()
    return render_template('home.html', projects=projects, menu=menu,
                           copyright='CC-BY-SA')

@limiter.limit("4 per day")
@bookcloud.route('/new', methods = ['GET', 'POST'])
@login_required
def new():
    menu = menu_bar()
    form = IdentifierForm(request.form)
    if request.method == 'POST' and form.validate():
        user_repo_path = join('repos', form.name.data)
        if os.path.isdir(user_repo_path):
            flash(_('This project name already exists'), 'error')
        else:
            create_project(form.name.data, current_user)
            flash(_('Project created successfuly!'), 'info')
            return redirect(url_for('.project',
                                    project=form.name.data))
    return render_template('new.html', menu=menu, form=form)

@limiter.exempt
@bookcloud.route('/<project>')
def project(project):
    path = join('repos', project)
    branches = [d for d in os.listdir(path) if isdir(join(path, d))]
    menu = menu_bar(project)
    project_id = Project.query.filter_by(name=project).first().id
    master = Branch.query.filter_by(project_id=project_id, name='master').first()
    tree = [ get_sub_branches(master) ]
    log = get_log(project, 'master')
    master_path = join('repos', project, 'master', 'source')
    files = [f for f in os.listdir(master_path)
             if isfile(join(master_path, f)) and f[0] != '.']
    files.sort()
    files = [(splitext(f)[0], splitext(f)[1], int(os.stat(join(master_path, f)).st_size / 500)) for f in files]
    threads = (Thread.query.filter_by(project_id=project_id)
               .order_by(desc(Thread.posted_at)))
    return render_template('project.html', tree=tree, log=log, menu=menu, threads=threads,
                           files=files, show_discussion=True)

@bookcloud.route('/<project>/<branch>', methods = ['GET', 'POST'])
def branch(project, branch):
    if (current_user.is_authenticated):
        if (current_user.username == get_branch_owner(project, branch) or
            current_user.username == get_branch_owner(project, 'master')):
            merge_pendencies = get_merge_pendencies(project, branch)
            if merge_pendencies:
                return merge_pendencies
    menu = menu_bar(project, branch)
    log = get_log(project, branch)
    project_id = Project.query.filter_by(name=project).first().id
    threads = Thread.query.filter_by(project_id=project_id).order_by(desc(Thread.posted_at))
    return render_template('branch.html', menu=menu, log=log, render_sidebar=False)

@limiter.limit("7 per day")
@bookcloud.route('/<project>/<branch>/clone', methods = ['GET', 'POST'])
@login_required
def clone(project, branch):
    menu = menu_bar(project, branch)
    form = IdentifierForm(request.form)
    merge_pendencies = get_merge_pendencies(project, branch)
    if merge_pendencies:
        flash('???', 'error')
        return render_template('merge.html', menu=menu, form=form)
    if request.method == 'POST' and form.validate():
        new_repo_path = join('repos', project, form.name.data)
        if os.path.isdir(new_repo_path):
            flash(_('This branch name already exists'), 'error')
            return redirect(url_for('.clone', project=project, branch=branch))
        else:
            new_branch = request.form['name']
            create_branch(project, branch, new_branch, current_user.username)
            flash(_('Project cloned successfuly!'), 'info')
            return redirect(url_for('.view', project=project, branch=new_branch,
                                    filename='index.html'))
    return render_template('clone.html', menu=menu, form=form)

# Fix this, newfile should not have a branch
@bookcloud.route('/<project>/<branch>/newfile', methods = ['GET', 'POST'])
@login_required
def newfile(project, branch):
    menu = menu_bar(project, branch)
    form = IdentifierForm(request.form)
    if current_user.username != get_branch_owner(project, 'master'):
        flash(_('You are not the owner of master'), 'error')
        return redirect(url_for('.view', project=project,
                                branch=branch, filename='index.html'))
    merge_pendencies = get_merge_pendencies(project, branch)
    if merge_pendencies:
        return merge_pendencies
    if request.method == 'POST' and form.validate():
        filename = form.name.data
        file_extension = '.rst'
        file_path = join('repos', project, branch, 'source', filename + file_extension)
        if os.path.isfile(file_path):
            flash(_('This file name name already exists'), 'error')
        else:
            #file = open(file_path, 'w+')
            stars = '*' * len(filename) + '\n'
            #file.write(stars + filename + '\n' + stars)
            write_file(file_path, stars + filename + '\n' + stars)
            repo = git.Repo(join('repos', project, branch, 'source'))
            repo.index.add([filename + file_extension])
            #author = git.Actor(current_user.username, current_user.email)
            #repo.index.commit(_('Adding file %s' % filename), author=author)
            flash(_('File created successfuly!'), 'info')
            build(project, branch)
            return redirect(url_for('.view', project=project,
                                    branch=branch, filename='index.html'))
    return render_template('newfile.html', menu=menu, form=form)

@bookcloud.route('/<project>/renamefile/<oldfilename>', methods = ['GET', 'POST'])
@login_required
def renamefile(project, oldfilename):
    menu = menu_bar(project, 'master')
    form = IdentifierForm(request.form)
    if current_user.username != get_branch_owner(project, 'master'):
        flash(_('You are not the owner of master'), 'error')
        return redirect(url_for('.view', project=project,
                                branch='master', filename='index.html'))
    merge_pendencies = get_merge_pendencies(project, 'master')
    if merge_pendencies:
        return merge_pendencies
    if request.method == 'POST' and form.validate():
        filename = form.name.data
        file_extension = '.rst'
        file_path = join('repos', project, 'master', 'source', filename + file_extension)
        if os.path.isfile(file_path):
            flash(_('This file name already exists'), 'error')
        else:
            git_api = get_git(project, 'master')
            git_api.mv(oldfilename + file_extension, form.name.data + file_extension)
            #author = git.Actor(current_user.username, current_user.email)
            #repo.index.commit(_('Adding file %s' % filename), author=author)
            flash(_('File renamed successfuly!'), 'info')
            build(project, 'master')
            return redirect(url_for('.view', project=project,
                                    branch='master', filename='index.html'))
    return render_template('newfile.html', menu=menu, form=form)

@bookcloud.route('/<project>/deletefile/<filename>')
@login_required
def deletefile(project, filename):
    menu = menu_bar(project, 'master')
    if current_user.username != get_branch_owner(project, 'master'):
        flash(_('You are not the owner of master'), 'error')
        return redirect(url_for('.view', project=project,
                                branch='master', filename='index.html'))
    merge_pendencies = get_merge_pendencies(project, 'master')
    if merge_pendencies:
        return merge_pendencies
    file_extension = '.rst'
    file_path = join('repos', project, 'master', 'source', filename + file_extension)
    if not os.path.isfile(file_path):
        flash(_('This file does not exist'), 'error')
        return redirect(url_for('.view', project=project,
                                branch='master', filename='index.html'))
    if not os.stat(file_path).st_size == 0:
        flash(_('This file is not empty'), 'error')
        return redirect(url_for('.view', project=project,
                                branch='master', filename='index.html'))
    git_api = get_git(project, 'master')
    git_api.rm('-f', filename + file_extension)
    #author = git.Actor(current_user.username, current_user.email)
    #repo.index.commit(_('Adding file %s' % filename), author=author)
    flash(_('File removed successfuly!'), 'info')
    build(project, 'master')
    return redirect(url_for('.view', project=project,
                            branch='master', filename='index.html'))

@bookcloud.route('/<project>/<branch>/requests')
@login_required
def requests(project, branch):
    if (current_user.username != get_branch_owner(project, branch) and
        current_user.username != get_branch_owner(project, 'master')):
        flash(_('You are not the owner of this branch'), 'error')
        return redirect(url_for('.view', project=project, branch=branch, filename='index.html'))
    if is_dirty(project, branch):
        flash(_('Commit your changes before reviewing requests'), 'error')
        return redirect(url_for('.branch', project=project, branch=branch))
    requests = get_requests(project, branch)
    menu = menu_bar(project, branch)
    return render_template('requests.html', unmerged=requests, menu=menu)

@bookcloud.route('/<project>/<branch>/finish')
@login_required
def finish(project, branch):
    if (current_user.username != get_branch_owner(project, branch) and
        current_user.username != get_branch_owner(project, 'master')):
        flash(_('You are not the owner of this branch'), 'error')
        return redirect(url_for('.view', project=project, branch=branch, filename='index.html'))
    merging = get_merging(project, branch)
    if not merging:
        flash(_('You are not merging'), 'error')
        return redirect(url_for('.view', project=project, branch=branch, filename='index.html'))
    if len(merging['modified']):
        flash(_('You still have unreviewed files'), 'error')
        return redirect(url_for('.merge', project=project, branch=branch, other=merging['branch']))
    git_api = get_git(project, branch)
    git_api.commit('-m', 'Merge ' + merging['branch'])
    merge_file_path = join('repos', project, branch, 'merging.json')
    os.remove(merge_file_path)
    origin = get_branch_origin(project, branch).name
    if branch != origin:
        git_api.push('origin', branch)
        flash(_('Page submitted to _%s') % origin, 'info')
    update_subtree(project, branch)
    flash(_('You have finished merging _%s') % merging['branch'], 'info')
    return redirect(url_for('.branch', project=project, branch=branch))

@bookcloud.route('/<project>/<branch>/commit', methods = ['GET', 'POST'])
@login_required
def commit(project, branch):
    if (current_user.username != get_branch_owner(project, branch) and
        current_user.username != get_branch_owner(project, 'master')):
        flash(_('You are not the owner of this or the master branch'), 'error')
        return redirect(url_for('.view', project=project, branch=branch, filename='index.html'))
    merging = get_merging(project, branch)
    if merging:
        flash(_('You need to finish merging'), 'error')
        return redirect(url_for('.merge', project=project, branch=branch, other=merging['branch']))
    user_repo_path = join('repos', project, branch)
    repo = git.Repo(join(user_repo_path, 'source'))
    form = MessageForm(request.form)
    if request.method == 'POST' and form.validate():
        author = git.Actor(current_user.username, current_user.email)
        if len(form.message.data):
            message = form.message.data
        else:
            message = _('Some changes')
        repo.index.commit(message, author=author)
        origin = get_branch_origin(project, branch).name
        if branch != origin:
            git_api = repo.git
            git_api.push('origin', branch)
            flash(_('Page submitted to _%s') % origin, 'info')
        update_subtree(project, branch)
        flash('Change commited', 'info')
        return redirect(url_for('.branch', project=project, branch=branch))
    menu = menu_bar(project, branch)
    diff = repo.git.diff('--cached')
    return render_template('commit.html', menu=menu, form=form, diff=diff)

@bookcloud.route('/<project>/<branch>/merge/<other>')
@login_required
def merge(project, branch, other):
    merging = get_merging(project, branch)
    if not merging:
        if is_dirty(project, branch):
            flash(_('Commit your changes before reviewing requests'), 'error')
            return redirect(url_for('.commit', project=project, branch=branch))
        # Check if other has something to merge
        git_api = get_git(project, branch)
        branches = string.split(git_api.branch())
        merged = string.split(git_api.branch('--merged'))
        if other in merged:
            flash(_('Branch _%s has no requests now') % other, 'error')
            return redirect(url_for('.view', project=project, branch=branch,
                                    filename='index.html'))
        git_api.merge('--no-commit', '--no-ff', '-s', 'recursive', '-Xtheirs', other)
        modified = string.split(git_api.diff('HEAD', '--name-only'))
        merging = {'branch': other, 'modified': modified, 'reviewed': []}
        write_file(join('repos', project, branch, 'merging.json'), json.dumps(merging))
    menu = {'right': [{'name': branch,
                       'url': url_for('.merge', project=project, branch=branch, other=other)}]}
    log = get_log(project, other)
    return render_template('merge.html', modified=merging['modified'],
                           reviewed=merging['reviewed'], other=other, log=log,
                           menu=menu)

@bookcloud.route('/<project>/<branch>/review/<path:filename>', methods = ['GET', 'POST'])
@login_required
def review(project, branch, filename):
    if (current_user.username != get_branch_owner(project, branch) and
        current_user.username != get_branch_owner(project, 'master')):
        flash(_('You are not the owner of this branch'), 'error')
        return redirect(url_for('.clone', project=project, branch=branch))
    merging = get_merging(project, branch)
    if not merging:
        flash(_('You are not merging'), 'error')
        return redirect(url_for('.view', project=project, branch=branch,
                                filename='index.html'))
    update_branch(project, branch)
    filename, file_extension = os.path.splitext(filename)
    branch_source_path = join('repos', project, branch, 'source', filename + '.rst')
    branch_html_path = join('repos', project, branch, 'build/html', filename + '.html')
    if request.method == 'POST':
        write_file(branch_source_path, request.form['code'])
        repo = git.Repo(join('repos', project, branch, 'source'))
        repo.index.add([filename + '.rst'])
        return redirect(url_for('.accept', project=project, branch=branch,
                                filename=filename + file_extension))
    branch_source_path = join('repos', project, branch, 'source', filename + '.rst')
    new = load_file(branch_source_path)
    git_api = get_git(project, branch)
    if git_api.ls_tree('-r', '--name-only', branch, filename + file_extension) != '':
        old = git_api.show(branch + ':' + filename + file_extension)
    else:
        old = ''
    menu = {'right': [{'name': branch,
                       'url': url_for('.edit', project=project,
                                      branch=branch, filename=filename)}]}
    return render_template('review.html', new=new, old=old,
                           filename=filename + file_extension,
                           menu=menu, other=merging['branch'], render_sidebar=False)

@bookcloud.route('/<project>/<branch>/diff/<path:filename>')
@login_required
def diff(project, branch, filename):
    if (current_user.username != get_branch_owner(project, branch) and
        current_user.username != get_branch_owner(project, 'master')):
        flash(_('You are not the owner of this branch'), 'error')
        return redirect(url_for('.view', project=project, branch=branch,
                                filename='index.html'))
    merging = get_merging(project, branch)
    if not merging:
        flash(_('You are not merging'), 'error')
        return redirect(url_for('.view', project=project, branch=branch,
                                filename='index.html'))
    #menu = menu_bar(project, branch)
    differ = HtmlDiff()
    filename, file_extension = os.path.splitext(filename)
    branch_source_path = join('repos', project, branch, 'source', filename + '.rst')
    new = string.split(load_file(branch_source_path), '\n')
    git_api = get_git(project, branch)
    if git_api.ls_tree('-r', '--name-only', branch, filename + file_extension) != '':
        old = string.split(git_api.show(branch + ':' + filename + file_extension), '\n')
    else:
        old = ''
    diff = differ.make_table(new, old)
    diff = string.replace(diff, 'nowrap="nowrap"', '')
    return render_template('diff.html', other=merging['branch'],
                           diff=diff, filename=filename + file_extension)

@bookcloud.route('/<project>/<branch>/accept/<path:filename>')
@login_required
def accept(project, branch, filename):
    if (current_user.username != get_branch_owner(project, branch) and
        current_user.username != get_branch_owner(project, 'master')):
        flash(_('You are not the owner of this branch'), 'error')
        return redirect(url_for('.view', project=project, branch=branch, filename='index.html'))
    merging = get_merging(project, branch)
    if not merging:
        flash(_('You are not merging'), 'error')
        return redirect(url_for('.view', project=project, branch=branch, filename='index.html'))
    if not filename in merging['modified']:
        flash('File %s is not being reviewed' % filename, 'error')
        return redirect(url_for('.view', project=project, branch=branch, filename='index.html'))
    merging['modified'].remove(filename)
    merging['reviewed'].append(filename)
    merge_file_path = join('repos', project, branch, 'merging.json')
    write_file(merge_file_path, json.dumps(merging))
    return redirect(url_for('.merge', project=project, branch=branch, other=merging['branch']))

from .threads import threads

app.register_blueprint(threads)


@limiter.exempt
@bookcloud.route('/<project>/<branch>/view/<path:filename>')
def view(project, branch, filename):
    filename, file_extension = os.path.splitext(filename)
    project_obj = Project.query.filter_by(name=project).first()
    if project_obj:
        project_id = project_obj.id
    else:
        return redirect(url_for('.home'))
    if file_extension == '':
        file_extension = '.html'
    user_repo_path = join('repos', project, branch,
                          'build/html', filename + file_extension)
    menu = menu_bar(project, branch)
    #update_branch(project, branch)
    if not current_user.is_authenticated:
        menu['right'].append({'url': url_for('.edit', project=project, branch=branch,
                                             filename=filename), 'name': 'edit'})
    else:
        if (current_user.username == get_branch_owner(project, branch) or
            current_user.username == get_branch_owner(project, 'master')):
            merge_pendencies = get_merge_pendencies(project, branch)
            if merge_pendencies:
                return merge_pendencies
            menu['right'].append({'url': url_for('.edit', project=project, branch=branch,
                                                 filename=filename), 'name': 'edit'})
        else:
            menu['right'].append({'url': url_for('.clone', project=project, branch=branch),
                                  'name': 'edit'})
    content = load_file(user_repo_path)
    threads = (Thread.query.join(File_Tag)
               .filter(File_Tag.filename==filename)
               .filter(Thread.project_id==project_id)
               .order_by(desc(Thread.posted_at)))
    label_list = []
    data = load_file(join('repos', project, branch,
                          'source', filename + '.rst'))
    label_list.extend([l for l in re.findall(r'^\.\. _([a-z\-]+):\s$', data, re.MULTILINE)])
    threads_by_tag = (db.session.query(File_Tag.filename, Thread.title)
                      .filter(File_Tag.filename.like(filename + '#' + '%'))
                      .filter(File_Tag.thread_id==Thread.id).all())
    threads_by_tag = [ {'name': name,
                        'fullname': filename + '%23' + name,
                        'titles': [x[1] for x in threads_by_tag
                                   if x[0].split('#')[1] == name]} for name in label_list]
#    print(threads_by_tag)
    return render_template_string(content, menu=menu, render_sidebar=True, threads=threads,
                                  threads_by_tag=threads_by_tag, show_discussion=False)

@limiter.exempt
@bookcloud.route('/<project>/<branch>/edit/<path:filename>', methods = ['GET', 'POST'])
@login_required
def edit(project, branch, filename):
    html_scroll = 0
    edit_scroll = 0
    if current_user.username != get_branch_owner(project, branch):
        flash(_('You are not the owner of this branch'), 'error')
        return redirect(url_for('.clone', project=project, branch=branch))
    merge_pendencies = get_merge_pendencies(project, branch)
    if merge_pendencies:
        return pendencies
    branch_source_path = join('repos', project, branch, 'source', filename + '.rst')
    branch_html_path = join('repos', project, branch, 'build/html', filename + '.html')
    if request.method == 'POST':
        html_scroll = request.form['html_scroll']
        edit_scroll = request.form['edit_scroll']
        write_file(branch_source_path, request.form['code'])
        repo = git.Repo(join('repos', project, branch, 'source'))
        flash(_('File saved successfully'), 'info')
        repo.index.add([filename + '.rst'])
    build(project, branch)
    rst = load_file(branch_source_path)
    doc = render_template_string(load_file(branch_html_path), barebones=True)
    menu = {'right': [{'name': branch,
                       'url': url_for('.edit', project=project, branch=branch, filename=filename)}]}
    return render_template('edit.html', doc=doc, rst=rst, filename=filename,
                           menu=menu, html_scroll=html_scroll,
                           edit_scroll=edit_scroll, render_sidebar=False)

@limiter.limit("300 per day")
@bookcloud.route('/html2rst', methods = ['GET', 'POST'])
def html2rst():
    if request.method == 'POST':
        print(request.form)
        if request.form.has_key('content'):
            input = request.form.get('content')
            if not input:
                input = 'undefined'
            if input != 'undefined':
                try:
                    converted = html2rest(input)
                    prefetch = None
                except:
                    converted = None
                    prefetch = input
                return render_template('html2rst.html', converted=converted,
                                       prefetch=prefetch)
    return render_template('html2rst.html')

@bookcloud.route('/<project>/pdf')
@bookcloud.route('/<project>/<branch>/pdf')
def pdf(project, branch='master'):
    build_path = os.path.abspath(join('repos', project, branch, 'build/latex'))
    build_latex(project, branch)
    command = '(cd ' + build_path + '; pdflatex -interaction nonstopmode linux.tex > /tmp/222 || true)'
    os.system(command)
    return flask.send_from_directory(build_path, 'linux.pdf')

@bookcloud.route('/<project>/<branch>/view/genindex.html')
def genindex(project, branch):
    return redirect(url_for('.view', project=project, branch=branch, filename='index.html'))

@limiter.exempt
@bookcloud.route('/<project>/<branch>/<action>/_images/<path:filename>')
#@bookcloud.route('/edit/<project>/<branch>/images/<path:filename>', methods = ['GET'])
def get_tikz(project, branch, action, filename):
    images_path = join('repos', project, branch, 'build/html/_images')
    return flask.send_from_directory(os.path.abspath(images_path), filename)

@limiter.exempt
@bookcloud.route('/<project>/<action>/_static/<path:filename>')
def get_static(project, action, filename):
    if (current_user.is_authenticated):
        user_repo_path = join('repos', project, current_user.username)
    else:
        user_repo_path = join('repos', project, get_creator(project))
    return flask.send_from_directory(os.path.abspath(join(user_repo_path, 'build/html/_static/')), filename)

@limiter.exempt
@bookcloud.route('/_static/<path:filename>')
def get_global_static(filename):
    return flask.send_from_directory(os.path.abspath(join('conf/biz/static/', os.path.dirname(filename))),
                                     os.path.basename(filename))

@bookcloud.route('/<project>/<branch>/view/_sources/<path:filename>')
def show_source(project, branch, filename):
    sources_path = join('repos', project, branch, 'build/html/_sources', filename)
    content = load_file(sources_path)
    return Response(content, mimetype='text/txt')

@limiter.exempt
@bookcloud.route('/<project>/images/<path:filename>')
def get_image(project, filename):
    return flask.send_from_directory(os.path.abspath('repos/' + project + '/images'), filename)

@limiter.exempt
@app.errorhandler(404)
def page_not_found(e):
    menu = menu_bar()
    return render_template('404.html', menu=menu), 404

#@bookcloud.errorhandler(500)
@limiter.exempt
@bookcloud.errorhandler(Exception)
def internal_server_error(e):
    message = repr(e)
    trace = traceback.format_exc()
    trace = string.split(trace, '\n')
    # send email to admin
    if (not app.config['TESTING']) and ('No such file or directory' not in message):
        print 'email'
        mail_message = message + '\n\n\n' + '\n'.join(trace)
        msg = Message('Error: ' + message[:40],
                      body=mail_message,
                      recipients=[app.config['ADMIN_MAIL']])
        mail.send(msg)
    return render_template('500.html', message=message,
                           trace=trace), 500

# @bookcloud.errorhandler(403)
# def page_forbidden(e):
#     return render_template('403.html'), 500


