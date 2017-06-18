from flask import Blueprint, render_template

from application.utils import display_threads
from application.threads import Thread, User_Tag

from application import app, limiter
from flask_user import login_required, current_user
from ..utils import menu_bar
from ..models import Project, Branch

from sqlalchemy import or_, desc

# app, db, User, Project, Branch, Thread, Comment, Likes, User_Tag, File_Tag, Named_Tag, Custom_Tag, Free_Tag, limiter, mail

my = Blueprint('my', __name__, url_prefix='/my')

@my.route('/login')
def login():
    return redirect(url_for('user.login'))

@my.route('/logout')
def logout():
    return redirect(url_for('user.logout'))

@limiter.exempt
@my.route('/profile')
@login_required
def profile():
    menu = menu_bar()
    projects = [d for d in Project.query.all()]
    collection = []
    for p in projects:
        user_branches = [b for b in Branch.query.filter_by(project_id=p.id,
                                                           owner_id=current_user.id)]
        if user_branches:
            collection.append({'project': p.name,
                               'branches': user_branches})
    threads = display_threads(Thread.query.join(User_Tag)
                              .filter(User_Tag.user_id==current_user.id)
                              .order_by(desc(Thread.posted_at)))
    return render_template('profile.html', user=current_user,
                           profile_form=app.config['USER_PROPERTIES'],
                           collection=collection, menu=menu, threads=threads,
                           show_discussion=False)

@limiter.limit("10 per day")
@my.route('/update_profile', methods = ['GET', 'POST'])
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
        return redirect(url_for('.profile'))

    return render_template('update_profile.html', user=current_user,
                           profile_form=app.config['USER_PROPERTIES'],
                           menu=menu, show_discussion=False)
