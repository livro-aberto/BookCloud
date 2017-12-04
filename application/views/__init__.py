import os
from os.path import join, isdir
import math
import time
import string
import urllib
import traceback
from datetime import datetime
import hashlib

from flask_user import login_required, current_user
from flask_babel import gettext as _

from flask import (
    g, Blueprint, request, render_template,
    url_for, flash, redirect
)
from flask import render_template, request, flash
from flask_user import current_user
from flask_babel import gettext as _
from flask_mail import Message

from application import app, mail, limiter, babel, db
from application.branches import *
from application.utils import last_modified, commit_diff, Custom404
from application.projects import Project, ProjectForm

@app.before_request
def bookcloud_before_request():
    g.menu = {
        'left': [{'name': 'Home',
                  'url': url_for('home')}],
        'right': [{
            'name': 'Bookcloud',
            'sub_menu': [
            {
                'name': 'Livro Aberto',
                'url': 'https://www.umlivroaberto.com',
                'external': True
            }, {
                'name': 'Issues',
                'url': 'https://github.com/gutosurrex/BookCloud/issues',
                'external': True
            }, {
                'name': 'Staff only',
                'url': 'https://www.umlivroaberto.com/wiki/doku.php',
                'external': True
            }, {
                'name': 'Syntax',
                'url': ('https://www.umlivroaberto.com/BookCloud/sintaxe/'
                        'master/view/index.html'),
                'external': True}]}]}
    if current_user.is_authenticated:
        g.menu['right'].append({
            'name': current_user.username,
            'sub_menu': [{
                'name': 'Profile',
                'url': url_for('users.profile')
            }, {
                'name': 'Logout',
                'url': url_for('user.logout')}]})
    else:
        g.menu['right'] = [
            {'name': 'Login', 'url': url_for('user.login')}]

@app.context_processor
def package():
    sent_package = {}
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
    sent_package['commit_diff'] = commit_diff
    return sent_package

@app.context_processor
def bookcloud_context_processor():
    return {'menu': g.menu}

@app.route('/')
@limiter.exempt
def home():
    path = 'repos'
    projects = [d.name for d in Project.query.all()]
    project_folders = [d for d in os.listdir(path) if isdir(join(path, d))]
    projects_without_folder = set(projects) - set(project_folders)
    if projects_without_folder:
        flash('Some projects have no folder (%s)'
              % ', '.join(projects_without_folder), 'error')
    folders_without_project = set(project_folders) - set(projects)
    if folders_without_project:
        flash('Some folders have no project (%s)'
              % ', '.join(folders_without_project), 'error')
    projects = list(set(projects) - set(projects_without_folder))
    return render_template('home.html', projects=projects)

@app.route('/new', methods = ['GET', 'POST'])
@limiter.limit("4 per day")
@login_required
def new():
    form = ProjectForm(request.form)
    if request.method == 'POST' and form.validate():
        user_repo_path = join('repos', form.name.data)
        if os.path.isdir(user_repo_path):
            flash(_('This project name already exists'), 'error')
        else:
            project = Project(form.name.data, current_user)
            db.session.add(project)
            db.session.commit()
            #project.create_project(form.name.data, current_user)
            flash(_('Project created successfuly!'), 'info')
            return redirect(url_for('branches.view',
                                    project=form.name.data,
                                    branch='master', filename='index'))
    return render_template('new.html', form=form)

@app.route('/html2rst', methods = ['GET', 'POST'])
@limiter.limit("300 per day")
def html2rst():
    if request.method == 'POST':
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

@babel.localeselector
def get_locale():
    # if a user is logged in, use the locale from the user settings
    # user = getattr(g, 'user', None)
    # if user is not None:
    #     return user.locale
    #print(request.accept_languages.best_match(app.config['LANGUAGES'].keys()))
    #return request.accept_languages.best_match(app.config['LANGUAGES'].keys())
    return 'en'

@limiter.exempt
@app.errorhandler(404)
@app.errorhandler(Custom404)
def page_not_found(e):
    bookcloud_before_request()
    message = e.message
    app.logger.error(message)
    return render_template('404.html', message=message), 404

@limiter.exempt
@app.errorhandler(Exception)
def internal_server_error(e):
    message = repr(e)
    app.logger.error(message)
    trace = traceback.format_exc()
    trace = string.split(trace, '\n')
    timestamp = (datetime.fromtimestamp(time.time())
                 .strftime('%Y-%m-%d %H:%M:%S'))
    if current_user.is_authenticated:
        user = current_user.username
    else:
        user = 'anonymous'
    gathered_data = ('message: {}\n\n\n'
                     'timestamp: {}\n'
                     'ip: {}\n'
                     'method: {}\n'
                     'request.scheme: {}\n'
                     'request.full_path: {}\n'
                     'user: {}\n\n\n'
                     'trace: {}'.format(message, timestamp,
                                        request.remote_addr, request.method,
                                        request.scheme, request.full_path,
                                        user, '\n'.join(trace)))
    # send email to admin
    if app.config['TESTING']:
        print(gathered_data)
    else:
        mail_message = gathered_data
        msg = Message('Error: ' + message[:40],
                      body=mail_message,
                      recipients=[app.config['ADMIN_MAIL']])
        mail.send(msg)
        flash(_('A message has been sent to the administrator'), 'info')
    bookcloud_before_request()
    return render_template('500.html', message=gathered_data), 500

