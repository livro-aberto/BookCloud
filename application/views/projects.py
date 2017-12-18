import os
import git
from os.path import join, isdir, isfile, splitext
from functools import wraps
import json

import flask
from flask import (
    g, Blueprint, request, render_template,
    url_for, flash, redirect, send_from_directory, abort
)
from flask_user import login_required, current_user
from flask_babel import gettext as _
from sqlalchemy import desc
from werkzeug import secure_filename, FileStorage
from PIL import Image
from shutil import copyfile

from application import db, app, limiter
from application.projects import (
    Project, ProjectForm, FileForm, new_file
)
from application.branches import (
    Branch, get_sub_branches,
    get_merge_pendencies
)
import application.views
from application.utils import (
    write_file, extension, lowercase_ext, resolve_conflict
)

IMAGES = tuple('jpg jpe jpeg png gif svg bmp'.split())

class UploadNotAllowed(Exception):
    """
    This exception is raised if the upload was not allowed. You should catch
    it in your view code and display an appropriate message to the user.
    """

projects = Blueprint('projects', __name__, url_prefix='/<project>')

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
    application.views.bookcloud_before_request()
    g.menu['left'].append({
            'name': _('Discussion'),
            'url': url_for('threads.query_thread', project=g.project.name),
            'external': True})
    g.menu['left'].append({
        'name': g.project.name,
        'sub_menu': [{
            'name': _('Visit master'),
            'url': url_for('branches.view', project=g.project.name,
                           branch='master', filename='index.html')
        }, {
            'name': _('Branches'),
            'url': url_for('projects.branches', project=g.project.name)
        }, {
            'name': _('Manage'),
            'url': url_for('projects.dashboard', project=g.project.name)
        }, {
            'name': _('View pdf'),
            'url': url_for('branches.pdf', project=g.project.name,
                           branch='master'),
            'external': True
        }, {
            'name': _('Upload Figure'),
            'url': url_for('projects.upload_resource', project=g.project.name),
            'external': True}]})

@projects.context_processor
def project_context_processor():
    return { 'project': g.project,
             'menu': g.menu }

@projects.route('/branches', methods = ['GET', 'POST'])
@limiter.exempt
def branches(project):
    return render_template('branches.html')

# Wrap in job queue
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
    return render_template('dashboard.html', tree=tree, log=log, files=files)

# Wrap in job queue
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
        #try:
        task = new_file.delay(project.id, form.name.data)
        #except application.projects.FileExists:
        #    flash(_('This file name name already exists'), 'error')
        #    return render_template('newfile.html', form=form)
        #flash(_('File created successfuly!'), 'info')
        return render_template(
            'waiting.html', task_id=task.task_id,
            next_url=url_for('projects.dashboard', project=project.name))
    return render_template('newfile.html', form=form)

# Wrap in job queue
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
            return redirect(url_for('branches.view',
                                    project=project.name,
                                    branch='master', filename=form.name.data))
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
        return redirect(url_for('branches.view', project=project.name,
                                branch='master', filename='index'))
    except application.projects.FileNotFound:
        flash(_('File not found'), 'error')
    except application.projects.FileNotEmpty:
        flash(_('This file is not empty'), 'error')
    return redirect(url_for('projects.dashboard', project=project.name))

# API routes
@projects.route('/upload_resource', methods = ['GET', 'POST'])
@login_required
def upload_resource(project):
    if request.method == 'GET':
        return '''
        <!doctype html>
        <title>Upload new File</title>
        <h1>Upload new File</h1>
        <form method=post enctype=multipart/form-data>
        <p><input type=file name=file>
        <input type=submit value=Upload>
        </form>
        '''
    if 'file' not in request.files:
        return json.dumps({
            'message': _('No file'),
            'status': 'error'
        })
    file = request.files['file']
    if file.filename == '':
        return json.dumps({
            'message': _('No selected file'),
            'status': 'error'
        })
    basename = lowercase_ext(secure_filename(file.filename))
    if extension(basename) not in IMAGES:
        return json.dumps({
            'message': _('File format not allowed'),
            'status': 'error'
        })
    folder = join(project.get_folder(), '_resources')
    original_folder = join(folder, 'original')
    if os.path.exists(join(original_folder, basename)):
        basename = resolve_conflict(original_folder, basename)
    target = join(original_folder, basename)
    file.save(target)
    # save low_resolution
    if extension(basename) == 'gif':
        copyfile(target, join(folder, 'low_resolution', basename))
        name, ext = os.path.splitext(basename)
        image = Image.open(target)
        image.save(join(folder, 'low_resolution', name + '.png'))
    else:
        image = Image.open(target)
        basewidth = 500
        wpercent = (basewidth/float(image.size[0]))
        hsize = int((float(image.size[1])*float(wpercent)))
        image = image.resize((basewidth,hsize), Image.ANTIALIAS)
        image.save(join(folder, 'low_resolution', basename))
    # save thumbnail
    image = Image.open(target)
    basewidth = 40
    wpercent = (basewidth/float(image.size[0]))
    hsize = int((float(image.size[1])*float(wpercent)))
    image = image.resize((basewidth,hsize), Image.ANTIALIAS)
    image.save(join(folder, 'thumbnail', basename))
    # here there has to be some thumbnailing
    if extension(basename) == 'gif':
        name, ext = os.path.splitext(basename)
        return ".. figure:: _resources/" + name + ".*"
    return ".. figure:: _resources/" + basename
    app.logger.info('Uploading file {} from project {}'.format(
        file.filename, project.name))
    return json.dumps({
        'message': _('Image saved successfully'),
        'status': 'success',
        'filename': basename
    })

# should be served by web server
# need to have webserver add project path
@projects.route('/resources/<path:filename>')
@limiter.exempt
def resources(project, filename):
    return send_from_directory(
        os.path.abspath(join(project.get_folder(), '_resources/original')),
        filename)

# should be served by web server
# need to have webserver add project path
# need to see all the cases of path:anything
@projects.route('/<path:anything>/_resources/<path:filename>')
@limiter.exempt
def other_resources(project, anything, filename):
    return flask.send_from_directory(
        os.path.abspath(join('application', 'static', 'bundles')),
        'file_not_found.png')
