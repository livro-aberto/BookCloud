import os
import git
import string
import json
from os.path import join

from flask_babel import gettext as _
from sqlalchemy import desc
from flask import (
    g, Blueprint, request, render_template, render_template_string,
    url_for, flash, redirect, send_from_directory
)
from flask_user import login_required, current_user

import application
from application import limiter
from application import db
from application.tools import load_file, write_file
from .projects import Project
from .threads import Thread, File_Tag
from application.branches import (
    Branch, BranchForm, CommitForm, get_branch_owner, get_merge_pendencies,
    build, get_merging, get_branch_origin, update_subtree, clone_branch,
    get_requests
)

branches = Blueprint('branches', __name__,
                     url_prefix='/branches/<project>/<branch>')

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
            flash(_('You have uncommitted changes!!!'), 'error')
            g.menu['right'].insert(0, {
                'url': url_for('branches.commit',
                               project=g.project.name,
                               branch=g.branch.name),
                'name': 'Commit', 'style': 'attention'
            })
        else:
            if len(get_requests(g.project.name, g.branch.name)):
                flash(_('You have unreviewed requests!!!'), 'error')
                g.menu['right'].insert(0, {
                    'url': url_for('branches.requests',
                                   project=g.project.name,
                                   branch=g.branch.name),
                    'name': 'Requests',
                    'style': 'attention'
                })

@branches.context_processor
def branch_context_processor():
    return { 'project': g.project,
             'branch': g.branch,
             'menu': g.menu }

@branches.route('/', methods = ['GET', 'POST'])
def branch(project, branch):
    # will be deprecated
    if (current_user.is_authenticated):
        if (current_user == branch.owner or
            current_user == project.get_master().owner):
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
    if (current_user.is_authenticated
        and (current_user == branch.owner or
             current_user == project.get_master().owner)):
            # will be deprecated
            merge_pendencies = get_merge_pendencies(project.name, branch.name)
            if merge_pendencies:
                return merge_pendencies
            ####################
    content = load_file(join('repos', project.name, branch.name,
                             'build/html', filename + file_extension))
    threads = (Thread.query.join(File_Tag)
               .filter(File_Tag.filename==filename)
               .filter(Thread.project_id==project.id)
               .order_by(desc(Thread.posted_at)))
    threads_by_tag = project.get_threads_by_tag(filename)
    return render_template('view.html', content=content,
                           threads=threads, filename=filename,
                           threads_by_tag=threads_by_tag)

@branches.route('/edit/<path:filename>', methods = ['GET', 'POST'])
@limiter.exempt
@login_required
def edit(project, branch, filename):
    html_scroll = 0
    edit_scroll = 0
    if current_user != branch.owner:
        flash(_('You are not the owner of this branch'), 'error')
        return redirect(url_for('branches.clone', project=project.name,
                                branch=branch.name))
    # will be deprecated
    merge_pendencies = get_merge_pendencies(project.name, branch.name)
    if merge_pendencies:
        return pendencies
    ####################
    branch_source_path = join('repos', project.name, branch.name,
                              'source', filename + '.rst')
    branch_html_path = join('repos', project.name, branch.name,
                            'build/html', filename + '.html')
    if request.method == 'POST':
        html_scroll = request.form['html_scroll']
        edit_scroll = request.form['edit_scroll']
        write_file(branch_source_path, request.form['code'])
        repo = git.Repo(join('repos', project.name, branch.name, 'source'))
        flash(_('File saved successfully'), 'info')
        repo.index.add([filename + '.rst'])
    build(project.name, branch.name)
    rst = load_file(branch_source_path)
    doc = render_template_string(load_file(branch_html_path), barebones=True)
    return render_template('edit.html', doc=doc, rst=rst, filename=filename,
                           html_scroll=html_scroll, edit_scroll=edit_scroll)

@branches.route('/clone', methods = ['GET', 'POST'])
@limiter.limit("7 per day")
@login_required
def clone(project, branch):
    form = BranchForm(request.form)
    merge_pendencies = get_merge_pendencies(project.name, branch.name)
    if merge_pendencies:
        flash('???', 'error')
        return render_template('merge.html', menu=menu, form=form)
    if request.method == 'POST' and form.validate():
        new_repo_path = join('repos', project.name, form.name.data)
        if os.path.isdir(new_repo_path):
            flash(_('This branch name already exists'), 'error')
            return redirect(url_for('branches.clone', project=project.name,
                                    branch=branch.name))
        else:
            new_branch_name = request.form['name']
            clone_branch(project, branch, new_branch_name, current_user)
            flash(_('Project cloned successfuly!'), 'info')
            return redirect(url_for('branches.view', project=project.name,
                                    branch=new_branch_name,
                                    filename='index.html'))
    return render_template('clone.html', form=form)

@branches.route('/requests')
@login_required
def requests(project, branch):
    if (current_user != branch.owner and
        current_user != project.get_master().owner):
        flash(_('You are not the owner of this branch'), 'error')
        return redirect(url_for('branches.view', project=project,
                                branch=branch, filename='index.html'))
    if project.get_branch(branch).is_dirty():
        flash(_('Commit your changes before reviewing requests'), 'error')
        return redirect(url_for('branches.branch', project=project.name,
                                branch=branch.name))
    requests = get_requests(project.name, branch.name)
    return render_template('requests.html', unmerged=requests, menu=menu)

@branches.route('/finish')
@login_required
def finish(project, branch):
    if (current_user != branch.owner and
        current_user != project.get_master().owner):
        flash(_('You are not the owner of this branch'), 'error')
        return redirect(url_for('branches.view', project=project,
                                branch=branch, filename='index.html'))
    # will be deprecated
    merging = get_merging(project, branch)
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
    origin = branch.origin
    if branch != origin:
        git_api.push('origin', branch)
        flash(_('Page submitted to _%s') % origin, 'info')
    update_subtree(project.name, branch.name)
    flash(_('You have finished merging _%s') % merging['branch'], 'info')
    return redirect(url_for('branches.branch', project=project.name,
                            branch=branch.name))

@branches.route('/commit', methods = ['GET', 'POST'])
@login_required
def commit(project, branch):
    if (current_user != branch.owner and
        current_user != project.get_master().owner):
        flash(_('You are not the owner of this or the master branch'), 'error')
        return redirect(url_for('branches.view', project=project.name,
                                branch=branch.name, filename='index.html'))
    # will be deprecated
    merging = get_merging(project, branch)
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
            flash(_('Page submitted to _%s') % origin, 'info')
        update_subtree(project.name, branch.name)
        flash('Change commited', 'info')
        return redirect(url_for('branches.branch', project=project.name,
                                branch=branch.name))
    diff = repo.git.diff('--cached')
    return render_template('commit.html', form=form, diff=diff)

@branches.route('/merge/<other>')
@login_required
def merge(project, branch, other):
    merging = get_merging(project, branch)
    if not merging:
        project_obj = Project.get_by_name(project)
        if project_obj.get_branch(branch).is_dirty():
            flash(_('Commit your changes before reviewing requests'), 'error')
            return redirect(url_for('branches.commit', project=project, branch=branch))
        # Check if other has something to merge
        git_api = get_git(project, branch)
        branches = string.split(git_api.branch())
        merged = string.split(git_api.branch('--merged'))
        if other in merged:
            flash(_('Branch _%s has no requests now') % other, 'error')
            return redirect(url_for('branches.view', project=project,
                                    branch=branch, filename='index.html'))
        git_api.merge('--no-commit', '--no-ff', '-s', 'recursive',
                      '-Xtheirs', other)
        modified = string.split(git_api.diff('HEAD', '--name-only'))
        merging = {'branch': other, 'modified': modified, 'reviewed': []}
        write_file(join('repos', project, branch, 'merging.json'),
                   json.dumps(merging))
    menu = {'right': [{'name': branch,
                       'url': url_for('branches.merge', project=project,
                                      branch=branch, other=other)}]}
    branch_obj = Branch.get_by_name(branch)
    log = branch_obj.get_log()
    return render_template('merge.html', modified=merging['modified'],
                           reviewed=merging['reviewed'], other=other, log=log,
                           menu=menu)

@branches.route('/review/<path:filename>', methods = ['GET', 'POST'])
@login_required
def review(project, branch, filename):
    if (current_user.username != get_branch_owner(project, branch) and
        current_user.username != get_branch_owner(project, 'master')):
        flash(_('You are not the owner of this branch'), 'error')
        return redirect(url_for('branches.clone', project=project, branch=branch))
    merging = get_merging(project, branch)
    if not merging:
        flash(_('You are not merging'), 'error')
        return redirect(url_for('branches.view', project=project, branch=branch,
                                filename='index.html'))
    update_branch(project, branch)
    filename, file_extension = os.path.splitext(filename)
    branch_source_path = join('repos', project, branch, 'source', filename + '.rst')
    branch_html_path = join('repos', project, branch, 'build/html', filename + '.html')
    if request.method == 'POST':
        write_file(branch_source_path, request.form['code'])
        repo = git.Repo(join('repos', project, branch, 'source'))
        repo.index.add([filename + '.rst'])
        return redirect(url_for('branches.accept', project=project, branch=branch,
                                filename=filename + file_extension))
    branch_source_path = join('repos', project, branch, 'source', filename + '.rst')
    new = load_file(branch_source_path)
    git_api = get_git(project, branch)
    if git_api.ls_tree('-r', '--name-only', branch, filename + file_extension) != '':
        old = git_api.show(branch + ':' + filename + file_extension)
    else:
        old = ''
    menu = {'right': [{'name': branch,
                       'url': url_for('branches.edit', project=project,
                                      branch=branch, filename=filename)}]}
    return render_template('review.html', new=new, old=old,
                           filename=filename + file_extension,
                           menu=menu, other=merging['branch'], render_sidebar=False)

@branches.route('/diff/<path:filename>')
@login_required
def diff(project, branch, filename):
    if (current_user.username != get_branch_owner(project, branch) and
        current_user.username != get_branch_owner(project, 'master')):
        flash(_('You are not the owner of this branch'), 'error')
        return redirect(url_for('branches.view', project=project, branch=branch,
                                filename='index.html'))
    merging = get_merging(project, branch)
    if not merging:
        flash(_('You are not merging'), 'error')
        return redirect(url_for('branches.view', project=project, branch=branch,
                                filename='index.html'))
    #menu = application.views.menu_bar(project, branch)
    differ = HtmlDiff()
    filename, file_extension = os.path.splitext(filename)
    branch_source_path = join('repos', project, branch, 'source', filename + '.rst')
    new = string.split(load_file(branch_source_path), '\n')
    git_api = get_git(project, branch)
    if git_api.ls_tree('-r', '--name-only', branch, filename + file_extension) != '':
        old = string.split(git_api.show(branch + ':' + filename + file_extension), '\n')
    else:
        old = ''
    diff = differ.make_table(new, old)
    diff = string.replace(diff, 'nowrap="nowrap"', '')
    return render_template('diff.html', other=merging['branch'],
                           diff=diff, filename=filename + file_extension)

@branches.route('/accept/<path:filename>')
@login_required
def accept(project, branch, filename):
    if (current_user.username != get_branch_owner(project, branch) and
        current_user.username != get_branch_owner(project, 'master')):
        flash(_('You are not the owner of this branch'), 'error')
        return redirect(url_for('branches.view', project=project, branch=branch, filename='index.html'))
    merging = get_merging(project, branch)
    if not merging:
        flash(_('You are not merging'), 'error')
        return redirect(url_for('branches.view', project=project, branch=branch, filename='index.html'))
    if not filename in merging['modified']:
        flash('File %s is not being reviewed' % filename, 'error')
        return redirect(url_for('branches.view', project=project, branch=branch, filename='index.html'))
    merging['modified'].remove(filename)
    merging['reviewed'].append(filename)
    merge_file_path = join('repos', project, branch, 'merging.json')
    write_file(merge_file_path, json.dumps(merging))
    return redirect(url_for('branches.merge', project=project, branch=branch, other=merging['branch']))

@branches.route('/pdf')
def pdf(project, branch='master'):
    build_path = os.path.abspath(join('repos', project, branch, 'build/latex'))
    build_latex(project, branch)
    command = '(cd ' + build_path + '; pdflatex -interaction nonstopmode linux.tex > /tmp/222 || true)'
    os.system(command)
    return flask.send_from_directory(build_path, 'linux.pdf')

@branches.route('/view/genindex.html')
def genindex(project, branch):
    return redirect(url_for('branches.view', project=project, branch=branch, filename='index.html'))

@limiter.exempt
@branches.route('/<action>/_images/<path:filename>')
#@temp.route('/edit/<project>/<branch>/images/<path:filename>', methods = ['GET'])
def get_tikz(project, branch, action, filename):
    images_path = join('repos', project.name, branch.name,
                       'build/html/_images')
    return send_from_directory(os.path.abspath(images_path), filename)
