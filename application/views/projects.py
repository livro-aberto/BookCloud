import os
import git
from os.path import join, isdir, isfile, splitext
from functools import wraps

from flask import (
    g, Blueprint, request, render_template,
    url_for, flash, redirect
)
from flask_user import login_required, current_user
from flask_babel import gettext as _
from sqlalchemy import desc

from application import db, limiter
from application.projects import Project, ProjectForm, FileForm
from application.threads import Thread
from application.branches import (
    Branch, get_sub_branches,
    get_merge_pendencies
)
import application.views
from application.tools import write_file

projects = Blueprint('projects', __name__, url_prefix='/projects/<project>')

def require_projct_owner(func):
    """
    A view decorator that restricts access to owner of project
    """
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if current_user != g.project.owner:
            flash(_('You are not the owner of this project'), 'error')
            return redirect(url_for('branches.view', project=g.project.name,
                                    branch='master', filename='index.html'))
        return func(*args, **kwargs)
    return decorated_function

@projects.url_value_preprocessor
def projects_url_value_preprocessor(endpoint, values):
    g.project = Project.get_by_name(values.get('project'))
    values['project'] = g.project

@projects.before_request
def projects_before_request():
    application.views.bookcloud.bookcloud_before_request()
    g.menu['left'].append({
        'name': g.project.name,
        'sub_menu': [{
            'name': 'View master index',
            'url': url_for('branches.view', project=g.project.name,
                           branch='master', filename='index.html')
        }, {
            'name': 'Dashboard',
            'url': url_for('projects.dashboard', project=g.project.name)
        }, {
            'name': 'Download pdf',
            'url': url_for('branches.pdf', project=g.project.name,
                           branch='master')
        }]})

@projects.context_processor
def project_context_processor():
    return { 'project': g.project,
             'menu': g.menu }

@projects.route('/dashboard', methods = ['GET', 'POST'])
@limiter.exempt
def dashboard(project):
    tree = [ get_sub_branches(project.get_master()) ]
    log = project.get_master().get_log()
    master_path = project.get_master().get_source_path()
    files = project.get_files()
    files.sort()
    files = [(splitext(f)[0], splitext(f)[1],
              int(os.stat(join(master_path, f)).st_size / 500)) for f in files]
    threads = (project.threads.order_by(desc(Thread.posted_at)))
    return render_template('dashboard.html', tree=tree, log=log,
                           files=files, threads=threads)

@projects.route('/newfile', methods = ['GET', 'POST'])
@login_required
@require_projct_owner
def newfile(project):
    form = FileForm(request.form)
    # will be deprecated
    merge_pendencies = get_merge_pendencies(project.name, 'master')
    if merge_pendencies:
        return merge_pendencies
    ####################
    if request.method == 'POST' and form.validate():
        try:
            project.new_file(form.name.data)
        except application.projects.FileExists:
            flash(_('This file name name already exists'), 'error')
            return render_template('newfile.html', form=form)
        flash(_('File created successfuly!'), 'info')
        return redirect(url_for('branches.view', project=project.name,
                                branch='master', filename='index.html'))
    return render_template('newfile.html', form=form)

@projects.route('/renamefile/<oldfilename>', methods = ['GET', 'POST'])
@login_required
@require_projct_owner
def renamefile(project, oldfilename):
    form = FileForm(request.form)
    # will be deprecated
    merge_pendencies = get_merge_pendencies(project.name, 'master')
    if merge_pendencies:
        return merge_pendencies
    ####################
    if request.method == 'POST' and form.validate():
        try:
            project.rename_file(oldfilename, form.name.data)
            flash(_('File renamed successfuly!'), 'info')
            return redirect(url_for('projects.dashboard',
                                    project=project.name))
        except application.projects.FileExists:
            flash(_('This file name already exists'), 'error')
        except application.projects.FileNotFound:
            flash(_('File not found'), 'error')
    return render_template('renamefile.html', old_name=oldfilename, form=form)

@projects.route('/deletefile/<filename>')
@login_required
@require_projct_owner
def deletefile(project, filename):
    # will be deprecated
    merge_pendencies = get_merge_pendencies(project.name, 'master')
    if merge_pendencies:
        return merge_pendencies
    ####################
    try:
        project.delete_file(filename)
        flash(_('File removed successfuly!'), 'info')
        return redirect(url_for('projects.dashboard',
                                    project=project.name))
    except application.projects.FileNotFound:
        flash(_('File not found'), 'error')
    except application.projects.FileNotEmpty:
        flash(_('This file is not empty'), 'error')
    project.get_master().build()
    return redirect(url_for('projects.dashboard', project=project.name))
