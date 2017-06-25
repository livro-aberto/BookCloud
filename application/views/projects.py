import os
from os.path import join, isdir

from flask import (
    Blueprint, request, render_template,
    url_for, flash, redirect
)
from flask_user import login_required, current_user
from flask_babel import gettext as _
from sqlalchemy import desc

from application import limiter
from application.users import User
from application.threads import *
from application.utils import menu_bar
from application.projects import *

projects = Blueprint('projects', __name__, url_prefix='/projects')

@limiter.exempt
@projects.route('/')
def home():
    path = 'repos'
    projects = [d.name for d in Project.query.all()]
    project_folders = [d for d in os.listdir(path) if isdir(join(path, d))]
    projects_without_folder = set(projects) - set(project_folders)
    if projects_without_folder:
        flash('Some projects have no folder (%s)' % ', '.join(projects_without_folder),
              'error')
    folders_without_project = set(project_folders) - set(projects)
    if folders_without_project:
        flash('Some folders have no project (%s)' % ', '.join(folders_without_project),
              'error')
    projects = list(set(projects) - set(projects_without_folder))
    menu = menu_bar()
    return render_template('home.html', projects=projects, menu=menu,
                           copyright='CC-BY-SA')

@limiter.limit("4 per day")
@projects.route('/new', methods = ['GET', 'POST'])
@login_required
def new():
    menu = menu_bar()
    form = ProjectForm(request.form)
    if request.method == 'POST' and form.validate():
        user_repo_path = join('repos', form.name.data)
        if os.path.isdir(user_repo_path):
            flash(_('This project name already exists'), 'error')
        else:
            create_project(form.name.data, current_user)
            flash(_('Project created successfuly!'), 'info')
            return redirect(url_for('.project',
                                    project=form.name.data))
    return render_template('new.html', menu=menu, form=form)

@limiter.exempt
@projects.route('/<project>')
def project(project):
    path = join('repos', project)
    branches = [d for d in os.listdir(path) if isdir(join(path, d))]
    menu = menu_bar(project)
    project_id = Project.query.filter_by(name=project).first().id
    master = Branch.query.filter_by(project_id=project_id, name='master').first()
    tree = [ get_sub_branches(master) ]
    log = get_log(project, 'master')
    master_path = join('repos', project, 'master', 'source')
    files = [f for f in os.listdir(master_path)
             if isfile(join(master_path, f)) and f[0] != '.']
    files.sort()
    files = [(splitext(f)[0], splitext(f)[1], int(os.stat(join(master_path, f)).st_size / 500)) for f in files]
    threads = (Thread.query.filter_by(project_id=project_id)
               .order_by(desc(Thread.posted_at)))
    return render_template('project.html', tree=tree, log=log, menu=menu, threads=threads,
                           files=files, show_discussion=True)
