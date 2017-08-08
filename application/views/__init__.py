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

# import special tools for this platform
from application.tools import window, rst2html, Command, load_file,\
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

@app.before_request
def before_request():
    flask.g.locale = get_locale()

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


@app.template_filter('force_unicode')
def force_unicode(s):
    """Do all kinds of magic to turn `s` into unicode"""
    # It's already unicode, don't do anything:
    #if isinstance(s, six.text_type):
    #    return s
    # Try some default encodings:
    try:
        return s.decode('utf-8')
    except UnicodeDecodeError as exc:
        pass
    try:
        return s.decode(locale.getpreferredencoding())
    except UnicodeDecodeError:
        pass
    if chardet is not None:
        # Try chardet, if available
        encoding = chardet.detect(s)['encoding']
        if encoding is not None:
            return s.decode(encoding)
    raise # Give up.

@app.template_filter('extract_author_name')
def extract_author_name(email):
    """Extract the name from an email address --
    >>> extract_author_name("John <john@example.com>")
    "John"
    -- or return the address if none is given.
    >>> extract_author_name("noname@example.com")
    "noname@example.com"
    """
    match = re.match('^(.*?)<.*?>$', email)
    if match:
        return match.group(1).strip()
    return email

@app.template_filter('formattimestamp')
def formattimestamp(timestamp):
    return (datetime.fromtimestamp(timestamp)
            .strftime('%b %d, %Y %H:%M:%S'))

@app.template_filter('timesince')
def timesince(when, now=time.time):
    """Return the difference between `when` and `now` in human
    readable form."""
    #return naturaltime(now() - when)
    return (now() - when)

@limiter.exempt
@temp.route('/<project>/<action>/_static/<path:filename>')
def get_static(project, action, filename):
    if (current_user.is_authenticated):
        user_repo_path = join('repos', project, current_user.username)
    else:
        user_repo_path = join('repos', project, get_creator(project))
    return flask.send_from_directory(os.path.abspath(join(user_repo_path, 'build/html/_static/')), filename)

@limiter.exempt
@temp.route('/_static/<path:filename>')
def get_global_static(filename):
    return flask.send_from_directory(os.path.abspath(join('conf/theme/static/', os.path.dirname(filename))),
                                     os.path.basename(filename))

@temp.route('/<project>/<branch>/view/_sources/<path:filename>')
def show_source(project, branch, filename):
    sources_path = join('repos', project, branch, 'build/html/_sources', filename)
    content = load_file(sources_path)
    return Response(content, mimetype='text/txt')

@limiter.exempt
@temp.route('/<project>/images/<path:filename>')
def get_image(project, filename):
    return flask.send_from_directory(os.path.abspath('repos/' + project + '/images'), filename)

@app.before_request
def projects_before_request():
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
    # send email to admin
    if ((not app.config['TESTING'])
        and ('No such file or directory' not in message)):
        gathered_data = ('timestamp: %s\n'
                         'ip: %s\n'
                         'method: %s\n'
                         'request.scheme: %s\n'
                         'request.full_path: %s\n'
                         'response.status: %s'
                         'user: %s',
                         timestamp, request.remote_addr,request.method,
                         request.scheme, request.full_path, response.status,
                         current_user)
        mail_message = (message + '\n\n\n' + '\n'.join(trace) + '\n\nData:\n'
                        + gathered_data)
        msg = Message('Error: ' + message[:40],
                      body=mail_message,
                      recipients=[app.config['ADMIN_MAIL']])
        mail.send(msg)
        flash(_('A message has been sent to the administrator'), 'info')
    return render_template('500.html', message=message), 500


