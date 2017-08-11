import os
import re
import math
import json
import time
from os.path import isdir, isfile, join, splitext
import flask
from flask import g
import urllib
from flask import render_template, render_template_string, request
from flask import redirect, url_for, Response, flash, Blueprint
from flask_user import login_required, SQLAlchemyAdapter, current_user
from sqlalchemy import or_, desc

from application import utils as utils

from application import app, db, mail, limiter
from application.diff import render_diff

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

# import special utils for this platform
from application.utils import window, rst2html, Command, load_file,\
    write_file, last_modified

import users

import projects

import bookcloud

import threads

import branches


mail.init_app(app)

config_path = 'conf'

temp = Blueprint('temp', __name__, template_folder='templates')

babel = Babel(app)

import pprint
pp = pprint.PrettyPrinter(indent=4).pprint


from ..utils import select_multi_checkbox

@babel.localeselector
def get_locale():
    # if a user is logged in, use the locale from the user settings
    # user = getattr(g, 'user', None)
    # if user is not None:
    #     return user.locale
    #print(request.accept_languages.best_match(app.config['LANGUAGES'].keys()))
    #return request.accept_languages.best_match(app.config['LANGUAGES'].keys())
    return 'en'


def commit_diff(repo, old_commit, new_commit):
    """Return the list of changes introduced from old to new commit."""
    summary = {'nfiles': 0, 'nadditions':  0, 'ndeletions':  0}
    file_changes = []  # the changes in detail
    dulwich_changes = repo.object_store.tree_changes(old_commit.tree,
                                                     new_commit.tree)
    for (oldpath, newpath), (oldmode, newmode), (oldsha, newsha) \
        in dulwich_changes:
        summary['nfiles'] += 1
        try:
            oldblob = (repo.object_store[oldsha] if oldsha
                       else Blob.from_string(b''))
            newblob = (repo.object_store[newsha] if newsha
                       else Blob.from_string(b''))
        except KeyError:
            # newsha/oldsha are probably related to submodules.
            # Dulwich will handle that.
            pass
        additions, deletions, chunks = render_diff(
            oldblob.splitlines(), newblob.splitlines())
        change = {
            'is_binary': False,
            'old_filename': oldpath or '/dev/null',
            'new_filename': newpath or '/dev/null',
            'chunks': chunks,
            'additions': additions,
            'deletions': deletions,
        }
        summary['nadditions'] += additions
        summary['ndeletions'] += deletions
        file_changes.append(change)
    return summary, file_changes

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

@app.before_request
def app_before_request():
    application.views.bookcloud.bookcloud_before_request()

@app.context_processor
def app_context_processor():
    return { 'menu': g.menu }

@limiter.exempt
@app.errorhandler(404)
def page_not_found(e):
    message = e.description
    return render_template('404.html', message=message), 404

@limiter.exempt
@app.errorhandler(Exception)
@app.route('/aaa')
def internal_server_error(e):
    message = repr(e)
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
                     'trace: {}'.format(
                     message, timestamp, request.remote_addr,request.method,
                     request.scheme, request.full_path,
                     user, '\n'.join(trace)))
    # send email to admin
    if not app.config['TESTING']:
        mail_message = gathered_data
        msg = Message('Error: ' + message[:40],
                      body=mail_message,
                      recipients=[app.config['ADMIN_MAIL']])
        mail.send(msg)
        flash(_('A message has been sent to the administrator'), 'info')
    print(gathered_data)
    return render_template('500.html', message=gathered_data), 500


