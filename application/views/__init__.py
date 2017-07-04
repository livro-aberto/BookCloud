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
from application import app, db, User, Thread, Comment, File_Tag, Named_Tag, Free_Tag, limiter, mail
from application.projects import Project
from application.branches import *
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

from application.threads import NewThreadForm

# import special tools for this platform
from application.tools import window, rst2html, Command, load_file,\
    write_file, last_modified


#import application.users
import users

import projects

import threads

#import application.branches
import branches


mail.init_app(app)

config_path = 'conf'

bookcloud = Blueprint('bookcloud', __name__, template_folder='templates')

babel = Babel(app)

import pprint
pp = pprint.PrettyPrinter(indent=4).pprint


from ..utils import select_multi_checkbox


def menu_bar(project=None, branch=None):
    left  = []
    right = []
    #if current_user.is_authenticated:
    if project:
        left.append({
            'name': project,
            'sub_menu': [{
                'name': 'View master',
                'url': url_for('branches.view', project=project,
                               branch='master', filename='index.html')
            }, {
                'name': 'Dashboard',
                'url': url_for('projects.project', project=project)
            }, {
                'name': 'Download pdf',
                'url': url_for('branches.pdf', project=project)
            }]})
        if branch:
            left.append({
                'name': branch,
                'sub_menu': [{
                    'name': 'View',
                    'url': url_for('branches.view', project=project,
                                   branch='master', filename='index.html')
                }, {
                    'name': 'Dashboard',
                    'url': url_for('branches.branch', project=project,
                                   branch=branch)
                }]})
            if current_user.is_authenticated:
                if current_user.username == get_branch_owner(project, branch):
                    if is_dirty(project, branch):
                        flash(_('You have uncommitted changes!!!'), 'error')
                        right.append({
                            'url': url_for('branches.commit',
                                           project=project,
                                           branch=branch),
                            'name': 'Commit', 'style': 'attention'
                        })
                    else:
                        if len(get_requests(project, branch)):
                            flash(_('You have unreviewed requests!!!'), 'error')
                            right.append({
                                'url': url_for('branches.requests',
                                               project=project,
                                               branch=branch),
                                'name': 'Requests',
                                'style': 'attention'
                            })
    if current_user.is_authenticated:
        right.append({'name': current_user.username,
                      'sub_menu': [{
                          'name': 'Profile',
                          'url': url_for('users.profile')
                      }, {
                          'name': 'Logout',
                          'url': url_for('user.logout')}]})
    else:
        right = [{'name': 'Login', 'url': url_for('user.login')}]
    return { 'left': left, 'right': right}


@babel.localeselector
def get_locale():
    # if a user is logged in, use the locale from the user settings
    # user = getattr(g, 'user', None)
    # if user is not None:
    #     return user.locale
    #print(request.accept_languages.best_match(app.config['LANGUAGES'].keys()))
    #return request.accept_languages.best_match(app.config['LANGUAGES'].keys())
    return 'en'

@app.before_request
def before_request():
    flask.g.locale = get_locale()

@app.context_processor
def package():
    sent_package = {}
    if (request.view_args) and ('project' in request.view_args):
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
    message = e.description
    trace = traceback.format_exc()
    trace = string.split(trace, '\n')
    return render_template('404.html', message=message,
                           trace=trace), 500

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


