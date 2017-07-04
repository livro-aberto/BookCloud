import os
import git
from os.path import join, isdir, isfile, splitext

from flask import (
    Blueprint, request, render_template,
    url_for, flash, redirect
)
from flask_user import login_required, current_user
from flask_babel import gettext as _
from sqlalchemy import desc

from application import limiter
from application.users import User
from application.threads import Thread
from application.branches import (
    Branch, get_sub_branches, get_log, get_branch_owner, get_merge_pendencies,
    get_git, build
)

from application.projects import (
    Project, ProjectForm, create_project, FileForm
)

import application.views

from application.tools import write_file

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
    menu = application.views.menu_bar()
    return render_template('home.html', projects=projects, menu=menu,
                           copyright='CC-BY-SA')

@limiter.limit("4 per day")
@projects.route('/new', methods = ['GET', 'POST'])
@login_required
def new():
    menu = application.views.menu_bar()
    form = ProjectForm(request.form)
    if request.method == 'POST' and form.validate():
        user_repo_path = join('repos', form.name.data)
        if os.path.isdir(user_repo_path):
            flash(_('This project name already exists'), 'error')
        else:
            create_project(form.name.data, current_user)
            flash(_('Project created successfuly!'), 'info')
            return redirect(url_for('projects.project',
                                    project=form.name.data))
    return render_template('new.html', menu=menu, form=form)

@limiter.exempt
@projects.route('/<project>')
def project(project):
    path = join('repos', project)
    branches = [d for d in os.listdir(path) if isdir(join(path, d))]
    menu = application.views.menu_bar(project)
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

# Fix this, newfile should not have a branch
@projects.route('/<project>/newfile', methods = ['GET', 'POST'])
@login_required
def newfile(project):
    menu = application.views.menu_bar(project)
    form = FileForm(request.form)
    if current_user.username != get_branch_owner(project, 'master'):
        flash(_('You are not the owner of master'), 'error')
        return redirect(url_for('branches.view', project=project,
                                branch='master', filename='index.html'))
    merge_pendencies = get_merge_pendencies(project, 'master')
    if merge_pendencies:
        return merge_pendencies
    if request.method == 'POST' and form.validate():
        filename = form.name.data
        file_extension = '.rst'
        file_path = join('repos', project, 'master', 'source', filename + file_extension)
        if os.path.isfile(file_path):
            flash(_('This file name name already exists'), 'error')
        else:
            #file = open(file_path, 'w+')
            stars = '*' * len(filename) + '\n'
            #file.write(stars + filename + '\n' + stars)
            write_file(file_path, stars + filename + '\n' + stars)
            repo = git.Repo(join('repos', project, 'master', 'source'))
            repo.index.add([filename + file_extension])
            #author = git.Actor(current_user.username, current_user.email)
            #repo.index.commit(_('Adding file %s' % filename), author=author)
            flash(_('File created successfuly!'), 'info')
            build(project, 'master')
            return redirect(url_for('branches.view', project=project,
                                    branch='master', filename='index.html'))
    return render_template('newfile.html', menu=menu, form=form)

@projects.route('/<project>/renamefile/<oldfilename>', methods = ['GET', 'POST'])
@login_required
def renamefile(project, oldfilename):
    menu = application.views.menu_bar(project, 'master')
    form = IdentifierForm(request.form)
    if current_user.username != get_branch_owner(project, 'master'):
        flash(_('You are not the owner of master'), 'error')
        return redirect(url_for('branches.view', project=project,
                                branch='master', filename='index.html'))
    merge_pendencies = get_merge_pendencies(project, 'master')
    if merge_pendencies:
        return merge_pendencies
    if request.method == 'POST' and form.validate():
        filename = form.name.data
        file_extension = '.rst'
        file_path = join('repos', project, 'master', 'source', filename + file_extension)
        if os.path.isfile(file_path):
            flash(_('This file name already exists'), 'error')
        else:
            git_api = get_git(project, 'master')
            git_api.mv(oldfilename + file_extension, form.name.data + file_extension)
            #author = git.Actor(current_user.username, current_user.email)
            #repo.index.commit(_('Adding file %s' % filename), author=author)
            flash(_('File renamed successfuly!'), 'info')
            build(project, 'master')
            return redirect(url_for('branches.view', project=project,
                                    branch='master', filename='index.html'))
    return render_template('newfile.html', menu=menu, form=form)

@projects.route('/<project>/deletefile/<filename>')
@login_required
def deletefile(project, filename):
    menu = application.views.menu_bar(project, 'master')
    if current_user.username != get_branch_owner(project, 'master'):
        flash(_('You are not the owner of master'), 'error')
        return redirect(url_for('branches.view', project=project,
                                branch='master', filename='index.html'))
    merge_pendencies = get_merge_pendencies(project, 'master')
    if merge_pendencies:
        return merge_pendencies
    file_extension = '.rst'
    file_path = join('repos', project, 'master', 'source', filename + file_extension)
    if not os.path.isfile(file_path):
        flash(_('This file does not exist'), 'error')
        return redirect(url_for('branches.view', project=project,
                                branch='master', filename='index.html'))
    if not os.stat(file_path).st_size == 0:
        flash(_('This file is not empty'), 'error')
        return redirect(url_for('branches.view', project=project,
                                branch='master', filename='index.html'))
    git_api = get_git(project, 'master')
    git_api.rm('-f', filename + file_extension)
    #author = git.Actor(current_user.username, current_user.email)
    #repo.index.commit(_('Adding file %s' % filename), author=author)
    flash(_('File removed successfuly!'), 'info')
    build(project, 'master')
    return redirect(url_for('branches.view', project=project,
                            branch='master', filename='index.html'))
