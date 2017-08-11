from flask import (Blueprint, render_template, request,
                   redirect, url_for, g, flash)
from flask_user import login_required, current_user
from flask_babel import gettext as _

from application import db
from application.projects import Project
from application import app, limiter
import application

users = Blueprint('users', __name__, url_prefix='/users')

@users.route('/login')
def login():
    return redirect(url_for('user.login'))

@users.route('/logout')
def logout():
    return redirect(url_for('user.logout'))

@users.before_request
def projects_before_request():
    application.views.bookcloud_before_request()

@users.context_processor
def threads_context_processor():
    return { 'menu': g.menu }

@users.route('/profile')
@limiter.exempt
@login_required
def profile():
    projects = list(Project.query.all())
    threads = current_user.threads
    return render_template('profile.html', projects=projects,
                           user=current_user,
                           properties=app.config['USER_PROPERTIES'],
                           threads=threads)

@users.route('/update_profile', methods = ['GET', 'POST'])
@limiter.limit("10 per day")
@login_required
def update_profile():
    if request.method == 'POST':
        for item in app.config['USER_PROPERTIES']:
            if request.form.has_key(item['variable']):
                if item['type'] == 'boolean':
                    if request.form[item['variable']] == 'yes':
                        setattr(current_user, item['variable'], True)
                    else:
                        setattr(current_user, item['variable'], False)
                if item['type'] == 'integer':
                    setattr(current_user, item['variable'],
                            item['choices']
                            .index(request.form[item['variable']]))
        db.session.commit()
        flash(_('Profile updated'), 'info')
        return redirect(url_for('users.profile'))
    return render_template('update_profile.html', user=current_user,
                           profile_form=app.config['USER_PROPERTIES'])
