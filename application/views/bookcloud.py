import os
from os.path import join, isdir

from flask import (
    Blueprint, request, render_template,
    url_for, flash, redirect
)
from flask_user import login_required, current_user
from flask_babel import gettext as _

from application import db, limiter

from application.projects import (
    Project, ProjectForm
)

import application.views

bookcloud = Blueprint('bookcloud', __name__)

@limiter.exempt
@bookcloud.route('/')
def home():
    path = 'repos'
    projects = [d.name for d in Project.query.all()]
    project_folders = [d for d in os.listdir(path) if isdir(join(path, d))]
    projects_without_folder = set(projects) - set(project_folders)
    if projects_without_folder:
        flash('Some projects have no folder (%s)'
              % ', '.join(projects_without_folder), 'error')
    folders_without_project = set(project_folders) - set(projects)
    if folders_without_project:
        flash('Some folders have no project (%s)'
              % ', '.join(folders_without_project), 'error')
    projects = list(set(projects) - set(projects_without_folder))
    menu = application.views.menu_bar()
    return render_template('home.html', projects=projects, menu=menu,
                           copyright='CC-BY-SA')

@limiter.limit("4 per day")
@bookcloud.route('/new', methods = ['GET', 'POST'])
@login_required
def new():
    menu = application.views.menu_bar()
    form = ProjectForm(request.form)
    if request.method == 'POST' and form.validate():
        user_repo_path = join('repos', form.name.data)
        if os.path.isdir(user_repo_path):
            flash(_('This project name already exists'), 'error')
        else:
            project = Project(form.name.data, current_user)
            db.session.add(project)
            db.session.commit()
            #project.create_project(form.name.data, current_user)
            flash(_('Project created successfuly!'), 'info')
            return redirect(url_for('projects.dashboard',
                                    project=form.name.data))
    return render_template('new.html', menu=menu, form=form)

