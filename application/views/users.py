from flask import (Blueprint, render_template, request,
                   redirect, url_for, g, flash)
from flask_user import login_required, current_user
from flask_babel import gettext as _

from application import db
from application.projects import Project
from application.branches import Branch
from application.threads import Named_Tag
from application import app, limiter
import application

from application.users import SubscriptionForm

users = Blueprint('users', __name__)

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
def users_context_processor():
    return { 'menu': g.menu }

@users.route('/profile')
@limiter.exempt
@login_required
def profile():
    projects = list(Project.query.all())
    branches = list(Branch.query.filter(Branch.owner==current_user).all())
    return render_template('profile.html', projects=projects, branches=branches,
                           user=current_user,
                           properties=app.config['USER_PROPERTIES'])

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

@users.route('/subscriptions', methods = ['GET', 'POST'])
@limiter.limit("10 per day")
@login_required
def subscriptions():
    form = SubscriptionForm(request.form)
    form.subscriptions.choices = [(str(t.id), t.project.name + ' - ' + t.name)
                                  for t in Named_Tag.query.all()]
    if request.method == 'POST' and form.validate():
        if not form.subscriptions.data:
            form.subscriptions.data = []
        subscription_list = (Named_Tag
            .query.filter(Named_Tag.id.in_(form.subscriptions.data))).all()
        current_user.subscriptions = subscription_list
        db.session.commit()
        flash(_('Subscriptions updated'), 'info')
        return redirect(url_for('users.profile'))
    form.subscriptions.default = [t.id for t in current_user.subscriptions]
    form.subscriptions.process(request.form)
    return render_template('subscriptions.html', form=form)
