from flask import url_for, flash

from flask_user import current_user
from users import User
from models import Project, Branch
from threads import Comment, User_Tag, File_Tag, Custom_Tag, Free_Tag, Likes
from application.tools import window, rst2html

from flask_babel import gettext as _



from tools import is_dirty, get_requests

def get_branch_owner(project, branch):
    project_obj = Project.query.filter_by(name=project).first()
    if project_obj:
        project_id = project_obj.id
        branch_obj = Branch.query.filter_by(project_id=project_id, name=branch).first()
        if branch_obj:
            return branch_obj.owner.username
    return None

def menu_bar(project=None, branch=None):
    left  = [{'url': url_for('bookcloud.home'), 'name': 'home'}]
    if current_user.is_authenticated:
        right = [{'url': url_for('user.logout'), 'name': 'logout'},
                    {'url': url_for('my.profile'), 'name': current_user.username}]
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

