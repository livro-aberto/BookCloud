import os
from os.path import join, isdir

from flask import (
    g, Blueprint, request, render_template,
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

@bookcloud.before_request
def bookcloud_before_request():
    g.menu = {'left': [], 'right': [{
        'name': 'Bookcloud',
        'sub_menu': [
        {
            'name': 'Issues',
            'url': 'https://github.com/gutosurrex/BookCloud/issues'
        }, {
            'name': 'Syntax',
            'url': ('https://www.umlivroaberto.com/BookCloud/sintaxe/'
                    'master/view/index.html')}]}]}
    if current_user.is_authenticated:
        g.menu['right'].append({
            'name': current_user.username,
            'sub_menu': [{
                'name': 'Profile',
                'url': url_for('users.profile')
            }, {
                'name': 'Logout',
                'url': url_for('user.logout')}]})
    else:
        g.menu['right'] = [
            {'name': 'Login', 'url': url_for('user.login')}]

@bookcloud.context_processor
def bookcloud_context_processor():
    return {'menu': g.menu}

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
    return render_template('home.html', projects=projects,
                           copyright='CC-BY-SA')

@limiter.limit("4 per day")
@bookcloud.route('/new', methods = ['GET', 'POST'])
@login_required
def new():
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
    return render_template('new.html', form=form)

@bookcloud.route('/html2rst', methods = ['GET', 'POST'])
@limiter.limit("300 per day")
def html2rst():
    if request.method == 'POST':
        if request.form.has_key('content'):
            input = request.form.get('content')
            if not input:
                input = 'undefined'
            if input != 'undefined':
                try:
                    converted = html2rest(input)
                    prefetch = None
                except:
                    converted = None
                    prefetch = input
                return render_template('html2rst.html', converted=converted,
                                       prefetch=prefetch)
    return render_template('html2rst.html')
