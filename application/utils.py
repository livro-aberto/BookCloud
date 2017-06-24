from flask import url_for, flash

from flask_user import current_user
from flask_babel import gettext as _
from wtforms.widgets import html_params

from users import *
from models import Project, Branch
from application.threads import Comment, File_Tag, Free_Tag
from application.tools import window, rst2html, load_file

import os
from os.path import join, isfile, splitext
from tools import is_dirty, get_requests
import json

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

def get_branch_owner(project, branch):
    project_obj = Project.query.filter_by(name=project).first()
    if project_obj:
        project_id = project_obj.id
        branch_obj = Branch.query.filter_by(project_id=project_id, name=branch).first()
        if branch_obj:
            return branch_obj.owner.username
    return None

def menu_bar(project=None, branch=None):
    left  = []
    right = []
    #if current_user.is_authenticated:
    if project:
        left.append({
            'name': project,
            'sub_menu': [{
                'name': 'View master',
                'url': url_for('bookcloud.view', project=project,
                               branch='master', filename='index.html')
            }, {
                'name': 'Dashboard',
                'url': url_for('bookcloud.project', project=project)
            }, {
                'name': 'Download pdf',
                'url': url_for('bookcloud.pdf', project=project)
            }]})
        if branch:
            left.append({
                'name': branch,
                'sub_menu': [{
                    'name': 'View',
                    'url': url_for('bookcloud.view', project=project,
                                   branch='master', filename='index.html')
                }, {
                    'name': 'Dashboard',
                    'url': url_for('bookcloud.branch', project=project,
                                   branch=branch)
                }]})
            if current_user.is_authenticated:
                if current_user.username == get_branch_owner(project, branch):
                    if is_dirty(project, branch):
                        flash(_('You have uncommitted changes!!!'), 'error')
                        right.append({
                            'url': url_for('bookcloud.commit',
                                           project=project,
                                           branch=branch),
                            'name': 'Commit', 'style': 'attention'
                        })
                    else:
                        if len(get_requests(project, branch)):
                            flash(_('You have unreviewed requests!!!'), 'error')
                            right.append({
                                'url': url_for('bookcloud.requests',
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

def get_labels(project):
    master_path = join('repos', project.name, 'master', 'source')
    label_list = []
    for f in os.listdir(master_path):
        if (isfile(join(master_path, f)) and f[0] != '.'):
            data = load_file(join(master_path, f))
            label_list.extend([splitext(f)[0] + '#' + l
                               for l in re.findall(r'^\.\. _([a-z\-]+):\s$', data, re.MULTILINE)])
    return json.dumps(label_list)
