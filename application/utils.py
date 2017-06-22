from flask import url_for, flash

from flask_user import current_user
from users import User
from models import Project, Branch
from application.threads import Comment, User_Tag, File_Tag, Custom_Tag, Free_Tag, Likes
from application.tools import window, rst2html

from flask_babel import gettext as _

from tools import is_dirty, get_requests

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
        left.append(
            {   'name': project,
                'sub_menu':
                [   {'name': 'dashboard', 'url': url_for('bookcloud.project', project=project)},
                    {'name': 'view master', 'url': url_for('bookcloud.view', project=project,
                                                           branch='master', filename='index.html')},
                    {'name': 'pdf', 'url': url_for('bookcloud.pdf', project=project)},
                ]})
        if branch:
            left.append(
                {   'name': branch,
                    'sub_menu':
                    [   {'name': 'dashboard', 'url': url_for('bookcloud.branch', project=project,
                                                             branch=branch)},
                        {'name': 'view', 'url': url_for('bookcloud.view', project=project,
                                                        branch='master', filename='index.html')}
                    ]})

            if current_user.is_authenticated:
                if current_user.username == get_branch_owner(project, branch):
                    if is_dirty(project, branch):
                        flash(_('You have uncommitted changes!!!'), 'error')
                        right.append({'url': url_for('bookcloud.commit', project=project, branch=branch),
                                      'name': 'commit', 'style': 'attention'})
                    else:
                        if len(get_requests(project, branch)):
                            flash(_('You have unreviewed requests!!!'), 'error')
                            right.append({'url': url_for('bookcloud.requests', project=project, branch=branch),
                                          'name': 'requests', 'style': 'attention'})
                right.append({'name': current_user.username,
                      'sub_menu':
                      [   {'name': 'profile', 'url': url_for('users.profile')},
                          {'name': 'logout', 'url': url_for('user.logout')}
                      ]})
            else:
                right = [{'name': 'login', 'url': url_for('user.login')}]


    return { 'left': left, 'right': right}

