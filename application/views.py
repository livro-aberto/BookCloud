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
from application import app, db, User, Project, Branch, Thread, Comment, Likes, User_Tag, File_Tag, Named_Tag, Custom_Tag, Free_Tag, limiter, mail
import string
from shutil import copyfile, rmtree
import git
from difflib import HtmlDiff
import traceback
from datetime import datetime, timedelta

from flask_babel import Babel, gettext as _

from flask_mail import Message

from wtforms import Form, BooleanField, StringField, validators,\
    RadioField, SelectMultipleField, TextAreaField, SelectField, HiddenField

from wtforms.widgets import html_params

# for identicon hashs
import hashlib

import sphinx

from creole import html2rest

# import special tools for this platform
from tools import window, rst2html, Command, get_git, load_file,\
    write_file, get_merging, get_requests, get_merge_pendencies,\
    config_repo, is_dirty, get_log, get_log_diff, last_modified

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

class CommentSearchForm(Form):
    search = StringField('Search', [ validators.Length(min=3, max=60)])

def select_multi_checkbox(field, ul_class='', **kwargs):
    kwargs.setdefault('type', 'checkbox')
    field_id = kwargs.pop('id', field.id)
    html = [u'<ul style="list-style-type: none; padding-left: 0px;" %s>' % html_params(id=field_id, class_=ul_class)]
    for value, label, checked in field.iter_choices():
        choice_id = u'%s-%s' % (field_id, value)
        options = dict(kwargs, name=field.name, value=value, id=choice_id)
        if checked:
            options['checked'] = 'checked'
        html.append(u'<li><input style="margin-left: 0px;" %s /> ' % html_params(**options))
        html.append(u'<label for="%s">%s</label></li>' % (field_id, label))
    html.append(u'</ul>')
    return u''.join(html)

class NewThreadForm(Form):
    title = StringField('Title', [ validators.Length(min=5, max=80)])
    flag = RadioField('Flag', choices = [('discussion', 'disucussion'),
                                         ('issue', 'issue')])
    usertags = SelectMultipleField('Users', widget=select_multi_checkbox)
    filetags = SelectMultipleField('Files', widget=select_multi_checkbox)
    namedtags = SelectMultipleField('Tags', widget=select_multi_checkbox)
    freetags = StringField('Hash Tags')
    firstcomment = TextAreaField('Content', [ validators.Length(min=3, max=2000)])

class EditThreadForm(Form):
    title = StringField('Title', [ validators.Length(min=5, max=80)])
    flag = RadioField('Flag', choices = [('discussion', 'disucussion'),
                                         ('issue', 'issue')])
    usertags = SelectMultipleField('Users', widget=select_multi_checkbox)
    filetags = SelectMultipleField('Files', widget=select_multi_checkbox)
    namedtags = SelectMultipleField('Tags', widget=select_multi_checkbox)
    freetags = StringField('Hash Tags')

class NewCommentForm(Form):
    comment = TextAreaField('Content', [ validators.Length(min=3, max=2000)])

def display_threads(threads):
    #***
    if not threads:
        return None
    response = []
    query = list(threads)
    for q in query:
        current_thread = {}
        current_thread['id'] = q.id
        current_thread['title'] = q.title
        current_thread['author'] = User.query.filter_by(id=q.owner_id).first().username
        current_thread['flag'] = q.flag
        current_thread['posted_at'] = q.posted_at
        current_thread['number'] = Comment.query.filter_by(thread_id=q.id).count()
        user_tags = User_Tag.query.filter_by(thread_id=q.id)
        current_thread['user_tags'] = [u.user.username for u in user_tags]
        file_tags = File_Tag.query.filter_by(thread_id=q.id)
        current_thread['file_tags'] = [f.filename for f in file_tags]
        custom_tags = Custom_Tag.query.filter_by(thread_id=q.id)
        current_thread['custom_tags'] = [c.named_tag.name for c in custom_tags]
        free_tags = Free_Tag.query.filter_by(thread_id=q.id)
        current_thread['free_tags'] = [f.name for f in free_tags]
        current_thread['comments'] = []

        get_comments = Comment.query.filter_by(thread_id=q.id).order_by(Comment.lineage).limit(100)
        for prev_comment, comment, next_comment  in window(get_comments):
            current_comment = {}
            current_comment['id'] = comment.id
            current_comment['author'] = User.query.filter_by(id=comment.owner_id).first().username
            try:
                current_comment['content'] = rst2html(comment.content)
            except:
                current_comment['content'] = _('Error in compiling comment:\n\n' + comment.content)
            current_comment['posted_at'] = comment.posted_at
            current_comment['lineage'] = comment.lineage
            current_comment['indent'] = 6 * len(comment.lineage)
            current_comment['likes'] = Likes.query.filter_by(comment_id=comment.id).count()
            if next_comment:
                current_comment['father'] = (next_comment.lineage.startswith(comment.lineage))
            current_thread['comments'].append(current_comment)
        response.append(current_thread)

    return response

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
    copyfile('application/empty_repo/source/index.rst', join(repo_path, 'index.rst'))
    copyfile('application/empty_repo/.gitignore', join(repo_path, '.gitignore'))
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

def get_branch_owner(project, branch):
    project_obj = Project.query.filter_by(name=project).first()
    if project_obj:
        project_id = project_obj.id
        branch_obj = Branch.query.filter_by(project_id=project_id, name=branch).first()
        if branch_obj:
            return branch_obj.owner.username
    return None

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

def menu_bar(project=None, branch=None):
    left  = [{'url': url_for('bookcloud.home'), 'name': 'home'}]
    if current_user.is_authenticated:
        right = [{'url': url_for('user.logout'), 'name': 'logout'},
                    {'url': url_for('bookcloud.profile'), 'name': current_user.username}]
    else:
        right = [{'url': url_for('user.login'), 'name': 'login'}]
    if project:
        left.append({'url': url_for('bookcloud.project', project=project), 'name': project})
        if branch:
            left.append({'url': url_for('bookcloud.branch', project=project,
                                        branch=branch), 'name': branch})
            if current_user.is_authenticated:
                if current_user.username == get_branch_owner(project, branch):
                    if is_dirty(project, branch):
                        flash(_('You have uncommitted changes!!!'), 'error')
                        right.append({'url': url_for('.commit', project=project, branch=branch),
                                      'name': 'commit', 'style': 'attention'})
                    else:
                        if len(get_requests(project, branch)):
                            flash(_('You have unreviewed requests!!!'), 'error')
                            right.append({'url': url_for('.requests', project=project, branch=branch),
                                          'name': 'requests', 'style': 'attention'})
    return { 'left': left, 'right': right}

@bookcloud.route('/login')
def login():
    return redirect(url_for('user.login'))

@bookcloud.route('/logout')
def logout():
    return redirect(url_for('user.logout'))

@limiter.exempt
@bookcloud.route('/profile')
@login_required
def profile():
    menu = menu_bar()
    projects = [d for d in Project.query.all()]
    collection = []
    for p in projects:
        user_branches = [b for b in Branch.query.filter_by(project_id=p.id,
                                                           owner_id=current_user.id)]
        if user_branches:
            collection.append({'project': p.name,
                               'branches': user_branches})
    threads = display_threads(Thread.query.join(User_Tag)
                              .filter(User_Tag.user_id==current_user.id)
                              .order_by(desc(Thread.posted_at)))
    return render_template('profile.html', user=current_user,
                           profile_form=app.config['USER_PROPERTIES'],
                           collection=collection, menu=menu, threads=threads,
                           show_discussion=False)

@limiter.limit("10 per day")
@bookcloud.route('/update_profile', methods = ['GET', 'POST'])
@login_required
def update_profile():
    menu = menu_bar()

    if request.method == 'POST':
        for item in app.config['USER_PROPERTIES']:
            user = User.query.filter(User.username == current_user.username).first()
            if request.form.has_key(item['variable']):
                if item['type'] == 'boolean':
                    if request.form[item['variable']] == 'yes':
                        setattr(user, item['variable'], True)
                    else:
                        setattr(user, item['variable'], False)
                if item['type'] == 'integer':
                    setattr(user, item['variable'],
                            item['choices'].index(request.form[item['variable']]))

        db.session.commit()
        return redirect(url_for('.profile'))

    return render_template('update_profile.html', user=current_user,
                           profile_form=app.config['USER_PROPERTIES'],
                           menu=menu, show_discussion=False)

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
    #threads = display_threads(Thread.query.limit(10))
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
    threads = display_threads(Thread.query
                              .filter_by(project_id=project_id)
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
    threads = display_threads(Thread.query.filter_by(project_id=project_id).order_by(desc(Thread.posted_at)))
    return render_template('branch.html', menu=menu, log=log, render_sidebar=False)

@limiter.limit("50 per day")
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

@limiter.exempt
@bookcloud.route('/<project>/tagsthreads/<filetag>')
def tagthreads(project, filetag):
    menu = menu_bar(project)
    project_id = Project.query.filter_by(name=project).first().id
    threads = (display_threads(Thread.query.join(File_Tag)
                               .filter(File_Tag.filename.like('%' + filetag + '%'))
                               .filter(Thread.project_id==project_id)
                               .order_by(desc(Thread.posted_at))))
    return render_template('comments.html', menu=menu, threads=threads,
                           show_discussion=True)

@bookcloud.route('/<project>/comments', methods = ['GET', 'POST'])
def comments(project):
    menu = menu_bar(project)
    project_id = Project.query.filter_by(name=project).first().id
    form = CommentSearchForm(request.form)
    if request.method == 'POST' and form.validate():
        if not form.search.data:
            form.search.data = ""
        thread_query = (Thread.query.filter(Thread.project_id==project_id).
                        join(Comment).
                        filter(Comment.thread_id==Thread.id).
                        filter(or_(Comment.content.like('%' + form.search.data + '%'),
                                   Thread.title.like('%' + form.search.data + '%'))))
        threads = display_threads(thread_query.order_by(desc(Thread.posted_at)).limit(100))
    else:
        threads = display_threads(Thread.query
                                  .filter_by(project_id=project_id)
                                  .order_by(desc(Thread.posted_at)))
    return render_template('comments.html', menu=menu, threads=threads,
                           form=form, show_discussion=True)

@bookcloud.route('/<project>/newthread', methods = ['GET', 'POST'])
@login_required
def newthread(project):
    menu = menu_bar(project)
    project_id = Project.query.filter_by(name=project).first().id
    filters = {}
    default = {}
    filters["usertags"] = json.dumps([u.username for u in User.query.all()])
    master_path = join('repos', project, 'master', 'source')
    label_list = []
    for f in os.listdir(master_path):
        if (isfile(join(master_path, f)) and f[0] != '.'):
            data = load_file(join(master_path, f))
            label_list.extend([splitext(f)[0] + '#' + l
                               for l in re.findall(r'^\.\. _([a-z\-]+):\s$', data, re.MULTILINE)])
    filters["filetags"] = json.dumps(label_list)
    #    form.filetags.choices = [(splitext(f)[0], splitext(f)[0])
    #                             for f in os.listdir(master_path)
    #                             if isfile(join(master_path, f)) and f[0] != '.']
    if request.args.get('filetags', ''):
        default["filetags"] = json.dumps([request.args.get('filetags', '')])
    else:
        default["filetags"] = [""]
    filters["namedtags"] = json.dumps([t.name for t in Named_Tag.query.filter_by(project_id=project_id).all()])

    if request.method == 'POST':

        if ((request.form["title"] == "") or (request.form["firstcomment"] == "")):
            # Trying to recover when one entry was invalid
            # form.firstcomment.default = request.form['firstcomment']
            # form.title.default = request.form['title']
            # form.freetags.default = request.form['freetags']
            return render_template('newthread.html', filters=filters, default=default,
                                   menu=menu, show_discussion=False)
        else:
            owner = User.query.filter_by(username=current_user.username).first()
            # add thread
            new_thread = Thread(request.form['title'],
                                owner.id,
                                project_id,
                                request.form['flag'],
                                datetime.utcnow())
            db.session.add(new_thread)
            db.session.commit()
            # add first comment
            new_comment = Comment('000000:',
                                  new_thread.id,
                                  owner.id,
                                  request.form['firstcomment'],
                                  datetime.utcnow())
            db.session.add(new_comment)
            # add user tags
            for user in json.loads(request.form['usertags']):
                db.session.flush()
                user_id = User.query.filter_by(username=user).first().id
                new_usertag = User_Tag(new_thread.id, user_id)
                db.session.add(new_usertag)
            # add file tags
            for file in json.loads(request.form['filetags']):
                new_filetag = File_Tag(new_thread.id, file)
                db.session.add(new_filetag)
            # add named tags
            for tag in json.loads(request.form['namedtags']):
                db.session.flush()
                namedtag_id = Named_Tag.query.filter_by(project_id=project_id, name=tag).first().id
                new_namedtag = Custom_Tag(new_thread.id, namedtag_id)
                db.session.add(new_namedtag)
            # add free tags
            for freetag in filter(None, re.findall(r"[\w']+", request.form['freetags'])):
                new_freetag = Free_Tag(new_thread.id, freetag)
                db.session.add(new_freetag)

            db.session.commit()
            # send emails
            if not app.config['TESTING']:
                with mail.connect() as conn:
                    message_head = _('Thread: ') + request.form['title'] + '\n' +\
                                   _('Project: ') + project + '\n' +\
                                   _('Owner: ') + owner.username + '\n' +\
                                   _('Type: ') + request.form['flag'] + '\n' +\
                                   _('Created at: ') + str(datetime.utcnow()) + '\n' +\
                                   _('Contents:') + '\n\n'
                    links = _('To comment on this thread: ') +\
                            url_for('bookcloud.newcomment',
                                    project=project,
                                    thread_id = new_thread.id,
                                    _external = True)
                    for user in json.loads(request.form['usertags']):
                        user_obj = User.query.filter_by(username=user).first()
                        message = message_head + request.form['firstcomment'] + '\n\n' + links
                        subject = _('Thread: ') + request.form['title']
                        msg = Message(recipients=[user_obj.email],
                                      body=message,
                                      subject=subject)
                        conn.send(msg)

            flash(_('New thread successfully created'), 'info')
            if 'return_url' in request.args:
                return redirect(urllib.unquote(request.args['return_url']))

    return render_template('newthread.html', filters=filters, default=default,
                           menu=menu, show_discussion=False)

@bookcloud.route('/<project>/editthread/<thread_id>', methods = ['GET', 'POST'])
@login_required
def editthread(project, thread_id):
    menu = menu_bar(project)
    project_id = Project.query.filter_by(name=project).first().id
    thread_obj = Thread.query.filter_by(id=thread_id).first()
    if (current_user.username != thread_obj.owner.username and
        current_user.username != get_branch_owner(project, 'master')):
        flash(_('You are not allowed to edit this thread'), 'error')
        return redirect(url_for('.project', project=project))
    form = EditThreadForm(request.form)
    form.title.default = thread_obj.title
    form.flag.default = thread_obj.flag
    form.usertags.choices = [(u.username, u.username) for u in User.query.all()]
    form.usertags.default = [t.user.username for t in User_Tag.query.filter_by(thread_id=thread_id).all()]
    master_path = join('repos', project, 'master', 'source')
    label_list = []
    for f in os.listdir(master_path):
        if (isfile(join(master_path, f)) and f[0] != '.'):
            data = load_file(join(master_path, f))
            label_list.extend([(splitext(f)[0] + '#' + l, splitext(f)[0] + '#' + l)
                               for l in re.findall(r'^\.\. _([a-z\-]+):\s$', data, re.MULTILINE)])
    form.filetags.choices = label_list
    # form.filetags.choices = [(splitext(f)[0], splitext(f)[0])
    #                          for f in os.listdir(master_path)
    #                          if isfile(join(master_path, f)) and f[0] != '.']
    form.filetags.default = [t.filename for t in File_Tag.query.filter_by(thread_id=thread_id).all()]
    form.namedtags.choices = [(t.name, t.name) for t in Named_Tag.query.filter_by(project_id=project_id).all()]
    form.freetags.default = ', '.join([t.name for t in Free_Tag.query.filter_by(thread_id=thread_id).all()])

    if request.method == 'POST':
        if form.validate():
            owner = User.query.filter_by(username=current_user.username).first()
            # modify thread
            thread_obj.title = request.form['title']
            thread_obj.flag = request.form['flag']
            db.session.commit()
            # clear previous tags
            User_Tag.query.filter_by(thread_id=thread_id).delete()
            File_Tag.query.filter_by(thread_id=thread_id).delete()
            Custom_Tag.query.filter_by(thread_id=thread_id).delete()
            Free_Tag.query.filter_by(thread_id=thread_id).delete()
            db.session.commit()
            # add user tags
            for user in request.form.getlist('usertags'):
                db.session.flush()
                user_id = User.query.filter_by(username=user).first().id
                new_usertag = User_Tag(thread_id, user_id)
                db.session.add(new_usertag)
            # add file tags
            for file in request.form.getlist('filetags'):
                new_filetag = File_Tag(thread_id, file)
                db.session.add(new_filetag)
            # add named tags
            for tag in request.form.getlist('namedtags'):
                db.session.flush()
                namedtag_id = Named_Tag.query.filter_by(project_id=project_id, name=tag).first().id
                new_namedtag = Custom_Tag(thread_id, namedtag_id)
                db.session.add(new_namedtag)
            # add free tags
            for freetag in filter(None, re.findall(r"[\w']+", request.form['freetags'])):
                new_freetag = Free_Tag(thread_id, freetag)
                db.session.add(new_freetag)

            db.session.commit()

            flash(_('Thread successfully modified'), 'info')
            if 'return_url' in request.args:
                return redirect(urllib.unquote(request.args['return_url']))
        else:
            form.title.default = request.form['title']
            form.freetags.default = request.form['freetags']

    form.process()
    return render_template('editthread.html', menu=menu, form=form)


@bookcloud.route('/<project>/newcomment/<thread_id>', methods = ['GET', 'POST'])
@bookcloud.route('/<project>/newcomment/<thread_id>/<parent_lineage>', methods = ['GET', 'POST'])
@login_required
def newcomment(project, thread_id, parent_lineage=''):
    menu = menu_bar(project)
    form = NewCommentForm(request.form)

    if request.method == 'POST':
        if form.validate():
            project_id = Project.query.filter_by(name=project).first().id
            owner = User.query.filter_by(username=current_user.username).first()
            siblings_pattern = parent_lineage + '%'
            decend_comments = (Comment.query.filter(Comment.thread_id==thread_id)
                               .filter(Comment.lineage.like(siblings_pattern)).all())
            number_siblings = len(decend_comments)
            new_comment_lineage = parent_lineage + format(number_siblings, '06X') + ':'
            new_comment = Comment(new_comment_lineage,
                                  thread_id,
                                  owner.id,
                                  request.form['comment'],
                                  datetime.utcnow())
            db.session.add(new_comment)
            db.session.commit()
            # send emails
            if not app.config['TESTING']:
                with mail.connect() as conn:
                    thread = Thread.query.filter_by(id=thread_id).first()
                    list_of_users = [ tag.user.username for tag in User_Tag.query.filter_by(thread_id=thread_id) ]
                    message_head = _('Thread: ') + thread.title + '\n' +\
                                   _('Project: ') + project + '\n' +\
                                   _('Author: ') + owner.username + '\n' +\
                                   _('Type: ') + thread.flag + '\n' +\
                                   _('Created at: ') + str(datetime.utcnow()) + '\n' +\
                                   _('Contents:') + '\n\n'
                    links = _('To reply to this comment follow: ') +\
                            url_for('bookcloud.newcomment',
                                    project=project,
                                    thread_id=thread.id,
                                    parent_lineage=new_comment_lineage,
                                    _external=True)
                    for user in list_of_users:
                        user_obj = User.query.filter_by(username=user).first()
                        message = message_head + request.form['comment'] + '\n\n' + links
                        subject = _('Thread: ') + thread.title
                        msg = Message(recipients=[user_obj.email],
                                      body=message,
                                      subject=subject)
                        conn.send(msg)

            flash(_('New comment successfully created'), 'info')
            if 'return_url' in request.args:
                return redirect(urllib.unquote(request.args['return_url']))
        else:
            form.comment.default = request.form['comment']

    threads = display_threads(Thread.query.filter_by(id=thread_id).order_by(desc(Thread.posted_at)))
    form.process()
    return render_template('newcomment.html', menu=menu, form=form, threads=threads)

@bookcloud.route('/<project>/editcomment/<comment_id>', methods = ['GET', 'POST'])
@login_required
def editcomment(project, comment_id):
    menu = menu_bar(project)
    form = NewCommentForm(request.form)
    comment_obj = Comment.query.filter_by(id=comment_id).first()
    if current_user.username != comment_obj.owner.username:
        flash(_('You are not allowed to edit this comment'), 'error')
        return redirect(url_for('.project', project=project))
    form.comment.default = comment_obj.content
    if request.method == 'POST':
        if form.validate():
            comment_obj.content = request.form['comment']
            db.session.commit()

            flash(_('Comment modified successfully'), 'info')
            if 'return_url' in request.args:
                return redirect(urllib.unquote(request.args['return_url']))
        else:
            form.comment.default = request.form['comment']

    threads = display_threads(Thread.query.filter_by(id=comment_obj.thread_id).order_by(desc(Thread.posted_at)))
    form.process()
    return render_template('newcomment.html', menu=menu, form=form, threads=threads)

@bookcloud.route('/<project>/deletethread')
@login_required
def deletethread(project):
    thread_id = request.args['thread_id']
    if Comment.query.filter_by(thread_id=thread_id).first():
        flash(_('Thread is not empty'), 'error')
    else:
        thread = Thread.query.filter_by(id=thread_id).first()
        ownername = User.query.filter_by(id=thread.owner_id).first().username
        if not current_user.is_authenticated:
            flash(_('You must be logged in to delete a thread'), 'error')
        else:
            if current_user.username == ownername or current_user.username == get_branch_owner(project, 'master'):
                User_Tag.query.filter_by(thread_id=thread_id).delete()
                File_Tag.query.filter_by(thread_id=thread_id).delete()
                Custom_Tag.query.filter_by(thread_id=thread_id).delete()
                Free_Tag.query.filter_by(thread_id=thread_id).delete()
                Thread.query.filter_by(id=thread_id).delete()
                db.session.commit()
                flash(_('Thread successfully deleted'), 'info')
            else:
                flash(_('You are not allowed to delete this thread'), 'error')
    return redirect(urllib.unquote(request.args['return_url']))

@bookcloud.route('/<project>/deletecomment')
@login_required
def deletecomment(project):
    comment = Comment.query.filter_by(id=request.args['comment_id']).first()
    decendants = comment.lineage + '%'
    decend_comments = (Comment.query.filter(Comment.thread_id==comment.thread_id)
                       .filter(Comment.lineage.like(decendants)).all())
    if len(decend_comments) > 1:
        flash(_('This comment has replies and cannot be deleted'), 'error')
    else:
        if not current_user.is_authenticated:
            flash(_('You must be logged in to delete a comment'), 'error')
        else:
            ownername = User.query.filter_by(id=comment.owner_id).first().username
            if current_user.username == ownername or current_user.username == get_branch_owner(project, 'master'):
                Likes.query.filter_by(comment_id=comment.id).delete()
                Comment.query.filter_by(id=comment.id).delete()
                db.session.commit()
                flash(_('Comment successfully deleted'), 'info')
            else:
                flash(_('You are not allowed to delete this thread'), 'error')
    return redirect(urllib.unquote(request.args['return_url']))

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
    threads = (display_threads(Thread.query.join(File_Tag)
                               .filter(File_Tag.filename==filename)
                               .filter(Thread.project_id==project_id)
                               .order_by(desc(Thread.posted_at))))
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
@bookcloud.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

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


