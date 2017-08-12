import os
import git
import string
import json
import time
import os.path
from os.path import join
from functools import wraps
from difflib import HtmlDiff

import dulwich.repo

import flask

from flask_babel import gettext as _
from sqlalchemy import desc
from flask import (
    g, Blueprint, request, render_template,
    render_template_string, url_for, flash, redirect,
    send_from_directory, abort
)
from flask_user import login_required, current_user

import application
from application import limiter
from application import db
from application.utils import load_file, write_file
from .projects import Project
from .threads import Thread, File_Tag
from application.branches import (
    Branch, BranchForm, CommitForm, get_merge_pendencies,
    get_merging, update_subtree, get_requests, build_latex,
    update_branch
)

branches = Blueprint('branches', __name__,
                     url_prefix='/<project>/<branch>')

@branches.url_value_preprocessor
def branches_url_value_preprocessor(endpoint, values):
    g.project = Project.get_by_name(values.get('project'))
    values['project'] = g.project
    g.branch = g.project.get_branch(values.get('branch'))
    values['branch'] = g.branch

@branches.before_request
def branch_before_request():
    application.views.projects.projects_before_request()
    g.menu['left'].append({
        'name': g.branch.name,
        'sub_menu': [{
            'name': 'View index',
            'url': url_for('branches.view', project=g.project.name,
                           branch=g.branch.name, filename='index.html')
        }, {
            'name': 'Dashboard',
            'url': url_for('branches.branch', project=g.project.name,
                           branch=g.branch.name)
        }]})
    if current_user.is_authenticated and current_user == g.branch.owner:
        if g.branch.is_dirty():
            g.menu['right'].insert(0, {
                'url': url_for('branches.commit',
                               project=g.project.name,
                               branch=g.branch.name),
                'name': 'Commit', 'style': 'attention'
            })
        else:
            if len(get_requests(g.project.name, g.branch.name)):
                g.menu['right'].insert(0, {
                    'url': url_for('branches.requests',
                                   project=g.project.name,
                                   branch=g.branch.name),
                    'name': 'Requests',
                    'style': 'attention'
                })

def before_return(func):
    def func_wrapper(name, *args, **kargs):
        if current_user.is_authenticated and current_user == g.branch.owner:
            if g.branch.is_dirty():
                flash(_('You have uncommitted changes!!!'), 'error')
            else:
                if len(get_requests(g.project.name, g.branch.name)):
                    flash(_('You have unreviewed requests!!!'), 'error')
        return func(name, *args, **kargs)
    return func_wrapper

render_template = before_return(render_template)

@branches.context_processor
def branch_context_processor():
    return { 'project': g.project,
             'branch': g.branch,
             'menu': g.menu }

def require_branch_owner(func):
    """
    A view decorator that restricts access to owner of branch
    """
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if current_user != g.branch.owner:
            flash(_('You are not the owner of this branch'), 'error')
            return redirect(url_for('branches.view', project=g.project.name,
                                    branch=g.branch.name,
                                    filename='index.html'))
        return func(*args, **kwargs)
    return decorated_function

def require_branch_owner_or_master(func):
    """
    A view decorator that restricts access to owner of branch or master
    """
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if (current_user != g.branch.owner
            and current_user != g.project.get_master().owner):
            flash(_('You are not the owner of this branch nor of master'),
                  'error')
            return redirect(url_for('branches.view', project=g.project.name,
                                    branch=g.branch.name,
                                    filename='index.html'))
        return func(*args, **kwargs)
    return decorated_function

@branches.route('/', methods = ['GET', 'POST'])
def branch(project, branch):
    # will be deprecated
    if (current_user.is_authenticated and
        (current_user == branch.owner or
         current_user == project.get_master().owner)):
            merge_pendencies = get_merge_pendencies(project.name, branch.name)
            if merge_pendencies:
                return merge_pendencies
    ####################
    log = branch.get_log()
    threads = (Thread.query.filter_by(project_id=project.id).
               order_by(desc(Thread.posted_at)))
    return render_template('branch.html', log=log, threads=threads)

@branches.route('/view/<path:filename>')
@limiter.exempt
def view(project, branch, filename):
    filename, file_extension = os.path.splitext(filename)
    if file_extension == '':
        file_extension = '.html'
    g.menu['right'].insert(0, {'name': 'edit',
                               'url': url_for('branches.edit',
                                              project=project.name,
                                              branch=branch.name,
                                              filename=filename)})
    # will be deprecated
    if (current_user.is_authenticated and
        (current_user == branch.owner or
         current_user == project.get_master().owner)):
            merge_pendencies = get_merge_pendencies(project.name, branch.name)
            if merge_pendencies:
                return merge_pendencies
    ####################
    try:
        content = load_file(join('repos', project.name, branch.name,
                                 'build/html', filename + file_extension))
    except:
        abort(404)
    threads = (Thread.query.join(File_Tag)
               .filter(File_Tag.filename==filename)
               .filter(Thread.project_id==project.id)
               .order_by(desc(Thread.posted_at)).all())
    threads_by_tag = project.get_threads_by_tag(filename)
    return render_template('view.html', content=content,
                           threads=threads, filename=filename,
                           threads_by_tag=threads_by_tag)

@branches.route('/edit/<path:filename>', methods = ['GET', 'POST'])
@limiter.exempt
@login_required
def edit(project, branch, filename):
    if current_user != branch.owner:
        return redirect(url_for('.clone', project=project.name,
                                branch=branch.name))
    html_scroll = 0
    edit_scroll = 0
    # will be deprecated
    merge_pendencies = get_merge_pendencies(project.name, branch.name)
    if merge_pendencies:
        return pendencies
    ####################
    file_source_path = join(branch.get_source_path(), filename + '.rst')
    file_html_path = join(branch.get_html_path(), filename + '.html')
    if request.method == 'POST':
        html_scroll = request.form['html_scroll']
        edit_scroll = request.form['edit_scroll']
        write_file(file_source_path, request.form['code'])
        branch.get_repo().index.add([filename + '.rst'])
        flash(_('File saved successfully'), 'info')
        branch.build()
    rst = load_file(file_source_path)
    doc = load_file(file_html_path)
    return render_template('edit.html', doc=doc, rst=rst, filename=filename,
                           html_scroll=html_scroll, edit_scroll=edit_scroll)

@branches.route('/commit', methods = ['GET', 'POST'])
@login_required
def commit(project, branch):
    if (current_user != branch.owner and
        current_user != project.get_master().owner):
        flash(_('You are not the owner of this or the master branch'), 'error')
        return redirect(url_for('branches.view', project=project.name,
                                branch=branch.name, filename='index.html'))
    # will be deprecated
    merging = get_merging(project.name, branch.name)
    if merging:
        flash(_('You need to finish merging'), 'error')
        return redirect(url_for('branches.merge', project=project.name,
                                branch=branch.name, other=merging['branch']))
    ####################
    user_repo_path = join('repos', project.name, branch.name)
    repo = git.Repo(join(user_repo_path, 'source'))
    form = CommitForm(request.form)
    if request.method == 'POST' and form.validate():
        author = git.Actor(current_user.username, current_user.email)
        if len(form.message.data):
            message = form.message.data
        else:
            message = _('Some changes')
        repo.index.commit(message, author=author)
        origin = branch.origin
        if branch != origin:
            git_api = repo.git
            git_api.push('origin', branch.name)
            flash(_('Page submitted to _%s') % origin.name, 'info')
        update_subtree(project, branch)
        flash('Change commited', 'info')
        return redirect(url_for('branches.view', project=project.name,
                                branch=branch.name, filename='index'))
    diff = repo.git.diff('--cached')
    return render_template('commit.html', form=form, diff=diff)

@branches.route('/clone', methods = ['GET', 'POST'])
@limiter.limit("7 per day")
@login_required
def clone(project, branch):
    form = BranchForm(request.form)
    # will be deprecated
    merge_pendencies = get_merge_pendencies(project.name, branch.name)
    if merge_pendencies:
        flash(_('You are trying to clone a branch that is being merged'),
              'error')
        return render_template('merge.html')
    ####################
    if request.method == 'POST' and form.validate():
        if (Branch.query
            .filter_by(project_id=project.id, name=form.name.data).first()):
            flash(_('This branch name already exists'), 'error')
            return redirect(url_for('branches.clone', project=project.name,
                                    branch=branch.name))
        else:
            branch.clone(form.name.data, current_user)
            new_branch = project.get_branch(form.name.data)
            flash(_('Project cloned successfuly!'), 'info')
            start_time = time.time()
            # this while is a hack to wait for the build. waiting for celery...
            while (time.time() < start_time + 30
                   and not os.path.isfile(join(new_branch.get_html_path(),
                                               'index.html'))):
                pass
            return redirect(url_for('branches.view', project=project.name,
                                    branch=form.name.data,
                                    filename='index.html'))
    return render_template('clone.html', form=form)

@branches.route('/requests')
@login_required
@require_branch_owner_or_master
def requests(project, branch):
    if branch.is_dirty():
        flash(_('Commit your changes before reviewing requests'), 'error')
        return redirect(url_for('branches.branch', project=project.name,
                                branch=branch.name))
    requests = get_requests(project.name, branch.name)
    return render_template('requests.html', unmerged=requests)

@branches.route('/merge/<other>')
@login_required
@require_branch_owner_or_master
def merge(project, branch, other):
    merging = get_merging(project.name, branch.name)
    if not merging:
        if branch.is_dirty():
            flash(_('Commit your changes before reviewing requests'), 'error')
            return redirect(url_for('branches.commit', project=project.name,
                                    branch=branch.name))
        # Check if other has something to merge
        git_api = branch.get_git()
        branches = string.split(git_api.branch())
        merged = string.split(git_api.branch('--merged'))
        if other in merged:
            flash(_('Branch _%s has no requests now') % other, 'error')
            return redirect(url_for('branches.view', project=project.name,
                                    branch=branch.name, filename='index.html'))
        git_api.merge('--no-commit', '--no-ff', '-s', 'recursive',
                      '-Xtheirs', other)
        modified = string.split(git_api.diff('HEAD', '--name-only'))
        merging = {'branch': other, 'modified': modified, 'reviewed': []}
        write_file(join('repos', project.name, branch.name, 'merging.json'),
                   json.dumps(merging))
    g.menu = {'right': [{'name': branch.name,
                         'url': url_for('branches.merge', project=project.name,
                                        branch=branch.name, other=other)}]}
    # Logic for diff rendering
    repo = dulwich.repo.Repo(branch.get_source_path())
    try:
        old_commit = repo['refs/heads/' + branch.name.encode('utf8')]
        new_commit = repo['refs/heads/' + merging['branch'].encode('utf8')]
    except KeyError:
        raise
    return render_template('merge.html', modified=merging['modified'],
                           repo=repo, old_commit=old_commit,
                           new_commit=new_commit,
                           reviewed=merging['reviewed'], other=other)

@branches.route('/review/<path:filename>', methods = ['GET', 'POST'])
@login_required
@require_branch_owner_or_master
def review(project, branch, filename):
    merging = get_merging(project.name, branch.name)
    if not merging:
        flash(_('You are not merging'), 'error')
        return redirect(url_for('branches.view', project=project.name,
                                branch=branch.name,
                                filename='index.html'))
    update_branch(project, branch)
    filename, file_extension = os.path.splitext(filename)
    branch_source_path = join(branch.get_source_path(), filename + '.rst')
    branch_html_path = join(branch.get_html_path(), filename + '.html')
    if request.method == 'POST':
        write_file(branch_source_path, request.form['code'])
        repo = branch.get_repo()
        repo.index.add([filename + '.rst'])
        return redirect(url_for('branches.accept', project=project.name,
                                branch=branch.name,
                                filename=filename + file_extension))
    new = load_file(branch_source_path)
    git_api = branch.get_git()
    if (git_api.ls_tree('-r', '--name-only', branch.name,
                        filename + file_extension) != ''):
        old = git_api.show(branch.name + ':' + filename + file_extension)
    else:
        old = ''
    g.menu = {'right': [{'name': branch.name,
                         'url': url_for('branches.edit', project=project.name,
                                        branch=branch.name,
                                        filename=filename)}]}
    return render_template('review.html', new=new, old=old,
                           filename=filename + file_extension,
                           other=merging['branch'])

@branches.route('/accept/<path:filename>')
@login_required
@require_branch_owner_or_master
def accept(project, branch, filename):
    # will be deprecated
    merging = get_merging(project.name, branch.name)
    if not merging:
        flash(_('You are not merging'), 'error')
        return redirect(url_for('branches.view', project=project.name,
                                branch=branch.name, filename='index.html'))
    if not filename in merging['modified']:
        flash('File %s is not being reviewed' % filename, 'error')
        return redirect(url_for('branches.view', project=project.name,
                                branch=branch.name, filename='index.html'))
    ####################
    merging['modified'].remove(filename)
    merging['reviewed'].append(filename)
    merge_file_path = join('repos', project.name, branch.name, 'merging.json')
    write_file(merge_file_path, json.dumps(merging))
    return redirect(url_for('branches.merge', project=project.name,
                            branch=branch.name, other=merging['branch']))

@branches.route('/finish')
@login_required
@require_branch_owner_or_master
def finish(project, branch):
    # will be deprecated
    merging = get_merging(project.name, branch.name)
    if not merging:
        flash(_('You are not merging'), 'error')
        return redirect(url_for('branches.view', project=project.name,
                                branch=branch.name, filename='index.html'))
    if len(merging['modified']):
        flash(_('You still have unreviewed files'), 'error')
        return redirect(url_for('branches.merge', project=project.name,
                                branch=branch.name, other=merging['branch']))
    ####################
    git_api = branch.get_git()
    git_api.commit('-m', 'Merge ' + merging['branch'])
    merge_file_path = join('repos', project.name, branch.name, 'merging.json')
    os.remove(merge_file_path)
    if branch != branch.origin:
        git_api.push('origin', branch.name)
        flash(_('Page submitted to _%s') % branch.origin.name, 'info')
    update_subtree(project, branch)
    flash(_('You have finished merging _%s') % merging['branch'], 'info')
    return redirect(url_for('branches.view', project=project.name,
                            branch=branch.name, filename='index'))

@branches.route('/pdf')
def pdf(project, branch='master'):
    build_path = os.path.abspath(join('repos', project.name, branch.name, 'build/latex'))
    build_latex(project.name, branch.name)
    command = '(cd ' + build_path + '; pdflatex -interaction nonstopmode linux.tex > /tmp/222 || true)'
    os.system(command)
    return flask.send_from_directory(build_path, 'linux.pdf')

@branches.route('/view/genindex.html')
def genindex(project, branch):
    return redirect(url_for('branches.view', project=project, branch=branch, filename='index.html'))

@branches.route('/<action>/_images/<path:filename>')
@limiter.exempt
def get_tikz(project, branch, action, filename):
    images_path = join('repos', project.name, branch.name,
                       'build/html/_images')
    return send_from_directory(os.path.abspath(images_path), filename)
