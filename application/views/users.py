from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_user import login_required, current_user
from flask_babel import gettext as _
from sqlalchemy import or_, desc

from application import db
from application.threads import Thread
from application.users import User
from application import app, limiter

from ..utils import menu_bar
from ..models import Project, Branch

users = Blueprint('users', __name__, url_prefix='/users')

@users.route('/login')
def login():
    return redirect(url_for('user.login'))

@users.route('/logout')
def logout():
    return redirect(url_for('user.logout'))

@limiter.exempt
@users.route('/profile')
@login_required
def profile():
    menu = menu_bar('sabao', 'master')
    projects = [d for d in Project.query.all()]
    collection = []
    for p in projects:
        user_branches = [b for b in Branch.query.filter_by(project_id=p.id,
                                                           owner_id=current_user.id)]
        if user_branches:
            collection.append({'project': p.name,
                               'branches': user_branches})
    threads = current_user.tagged_threads
    return render_template('profile.html', user=current_user,
                           profile_form=app.config['USER_PROPERTIES'],
                           collection=collection, menu=menu, threads=threads,
                           show_discussion=False)

@limiter.limit("10 per day")
@users.route('/update_profile', methods = ['GET', 'POST'])
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
        flash(_('Profile updated'), 'info')
        return redirect(url_for('users.profile'))
    return render_template('update_profile.html', user=current_user,
                           profile_form=app.config['USER_PROPERTIES'],
                           menu=menu, show_discussion=False)
