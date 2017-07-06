import os
import re
import git
import string
import json
from os.path import join

from flask_babel import gettext as _
from sqlalchemy import desc
from flask import (
    Blueprint, request, render_template, render_template_string,
    url_for, flash, redirect
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
    get_log, is_dirty, get_git
)

branches = Blueprint('branches', __name__, url_prefix='/branches')

@branches.route('/<project>/<branch>', methods = ['GET', 'POST'])
def branch(project, branch):
    if (current_user.is_authenticated):
        if (current_user.username == get_branch_owner(project, branch) or
            current_user.username == get_branch_owner(project, 'master')):
            merge_pendencies = get_merge_pendencies(project, branch)
            if merge_pendencies:
                return merge_pendencies
    menu = application.views.menu_bar(project, branch)
    log = get_log(project, branch)
    project_id = Project.query.filter_by(name=project).first().id
    threads = (Thread.query.filter_by(project_id=project_id).
               order_by(desc(Thread.posted_at)))
    return render_template('branch.html', menu=menu, log=log, render_sidebar=False)

@limiter.limit("7 per day")
@branches.route('/<project>/<branch>/clone', methods = ['GET', 'POST'])
@login_required
def clone(project, branch):
    project = Project.get_by_name(project)
    branch = Branch.get_by_name(branch)
    menu = application.views.menu_bar(project.name, branch.name)
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
    return render_template('clone.html', menu=menu, form=form)

@branches.route('/<project>/<branch>/requests')
@login_required
def requests(project, branch):
    if (current_user.username != get_branch_owner(project, branch) and
        current_user.username != get_branch_owner(project, 'master')):
        flash(_('You are not the owner of this branch'), 'error')
        return redirect(url_for('branches.view', project=project, branch=branch, filename='index.html'))
    if is_dirty(project, branch):
        flash(_('Commit your changes before reviewing requests'), 'error')
        return redirect(url_for('branches.branch', project=project, branch=branch))
    requests = get_requests(project, branch)
    menu = application.views.menu_bar(project, branch)
    return render_template('requests.html', unmerged=requests, menu=menu)

@branches.route('/<project>/<branch>/finish')
@login_required
def finish(project, branch):
    if (current_user.username != get_branch_owner(project, branch) and
        current_user.username != get_branch_owner(project, 'master')):
        flash(_('You are not the owner of this branch'), 'error')
        return redirect(url_for('branches.view', project=project, branch=branch, filename='index.html'))
    merging = get_merging(project, branch)
    if not merging:
        flash(_('You are not merging'), 'error')
        return redirect(url_for('branches.view', project=project, branch=branch, filename='index.html'))
    if len(merging['modified']):
        flash(_('You still have unreviewed files'), 'error')
        return redirect(url_for('branches.merge', project=project, branch=branch, other=merging['branch']))
    git_api = get_git(project, branch)
    git_api.commit('-m', 'Merge ' + merging['branch'])
    merge_file_path = join('repos', project, branch, 'merging.json')
    os.remove(merge_file_path)
    origin = get_branch_origin(project, branch).name
    if branch != origin:
        git_api.push('origin', branch)
        flash(_('Page submitted to _%s') % origin, 'info')
    update_subtree(project, branch)
    flash(_('You have finished merging _%s') % merging['branch'], 'info')
    return redirect(url_for('branches.branch', project=project, branch=branch))

@branches.route('/<project>/<branch>/commit', methods = ['GET', 'POST'])
@login_required
def commit(project, branch):
    if (current_user.username != get_branch_owner(project, branch) and
        current_user.username != get_branch_owner(project, 'master')):
        flash(_('You are not the owner of this or the master branch'), 'error')
        return redirect(url_for('branches.view', project=project, branch=branch, filename='index.html'))
    merging = get_merging(project, branch)
    if merging:
        flash(_('You need to finish merging'), 'error')
        return redirect(url_for('branches.merge', project=project, branch=branch, other=merging['branch']))
    user_repo_path = join('repos', project, branch)
    repo = git.Repo(join(user_repo_path, 'source'))
    form = CommitForm(request.form)
    if request.method == 'POST' and form.validate():
        author = git.Actor(current_user.username, current_user.email)
        if len(form.message.data):
            message = form.message.data
        else:
            message = _('Some changes')
        repo.index.commit(message, author=author)
        origin = get_branch_origin(project, branch).name
        if branch != origin:
            git_api = repo.git
            git_api.push('origin', branch)
            flash(_('Page submitted to _%s') % origin, 'info')
        update_subtree(project, branch)
        flash('Change commited', 'info')
        return redirect(url_for('branches.branch', project=project, branch=branch))
    menu = application.views.menu_bar(project, branch)
    diff = repo.git.diff('--cached')
    return render_template('commit.html', menu=menu, form=form, diff=diff)

@branches.route('/<project>/<branch>/merge/<other>')
@login_required
def merge(project, branch, other):
    merging = get_merging(project, branch)
    if not merging:
        if is_dirty(project, branch):
            flash(_('Commit your changes before reviewing requests'), 'error')
            return redirect(url_for('branches.commit', project=project, branch=branch))
        # Check if other has something to merge
        git_api = get_git(project, branch)
        branches = string.split(git_api.branch())
        merged = string.split(git_api.branch('--merged'))
        if other in merged:
            flash(_('Branch _%s has no requests now') % other, 'error')
            return redirect(url_for('branches.view', project=project, branch=branch,
                                    filename='index.html'))
        git_api.merge('--no-commit', '--no-ff', '-s', 'recursive', '-Xtheirs', other)
        modified = string.split(git_api.diff('HEAD', '--name-only'))
        merging = {'branch': other, 'modified': modified, 'reviewed': []}
        write_file(join('repos', project, branch, 'merging.json'), json.dumps(merging))
    menu = {'right': [{'name': branch,
                       'url': url_for('branches.merge', project=project, branch=branch, other=other)}]}
    log = get_log(project, other)
    return render_template('merge.html', modified=merging['modified'],
                           reviewed=merging['reviewed'], other=other, log=log,
                           menu=menu)

@branches.route('/<project>/<branch>/review/<path:filename>', methods = ['GET', 'POST'])
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

@branches.route('/<project>/<branch>/diff/<path:filename>')
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

@branches.route('/<project>/<branch>/accept/<path:filename>')
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


@limiter.exempt
@branches.route('/<project>/<branch>/view/<path:filename>')
def view(project, branch, filename):
    filename, file_extension = os.path.splitext(filename)
    project_obj = Project.query.filter_by(name=project).first()
    if project_obj:
        project_id = project_obj.id
    else:
        return redirect(url_for('bookcloud.home'))
    if file_extension == '':
        file_extension = '.html'
    user_repo_path = join('repos', project, branch,
                          'build/html', filename + file_extension)
    menu = application.views.menu_bar(project, branch)
    #update_branch(project, branch)
    if not current_user.is_authenticated:
        menu['right'].append({'url': url_for('branches.edit', project=project, branch=branch,
                                             filename=filename), 'name': 'edit'})
    else:
        if (current_user.username == get_branch_owner(project, branch) or
            current_user.username == get_branch_owner(project, 'master')):
            merge_pendencies = get_merge_pendencies(project, branch)
            if merge_pendencies:
                return merge_pendencies
            menu['right'].append({'url': url_for('branches.edit', project=project, branch=branch,
                                                 filename=filename), 'name': 'edit'})
        else:
            menu['right'].append({'url': url_for('branches.clone', project=project, branch=branch),
                                  'name': 'edit'})
    content = load_file(user_repo_path)
    threads = (Thread.query.join(File_Tag)
               .filter(File_Tag.filename==filename)
               .filter(Thread.project_id==project_id)
               .order_by(desc(Thread.posted_at)))
    label_list = []
    data = load_file(join('repos', project, branch,
                          'source', filename + '.rst'))
    label_list.extend([l for l in re.findall(r'^\.\. _([a-z\-]+):\s$', data, re.MULTILINE)])
    threads_by_tag = (db.session.query(File_Tag.filename, Thread.title)
                      .filter(File_Tag.filename.like(filename + '#' + '%'))
                      .filter(File_Tag.thread_id==Thread.id).all())
    threads_by_tag = [
        {'name': name,
         'fullname': filename + '%23' + name,
         'titles': [x[1] for x in threads_by_tag
                    if x[0].split('#')[1] == name]} for name in label_list]
    return render_template_string(content, menu=menu, render_sidebar=True, threads=threads,
                                  threads_by_tag=threads_by_tag, show_discussion=False)

@limiter.exempt
@branches.route('/<project>/<branch>/edit/<path:filename>',
                methods = ['GET', 'POST'])
@login_required
def edit(project, branch, filename):
    html_scroll = 0
    edit_scroll = 0
    if current_user.username != get_branch_owner(project, branch):
        flash(_('You are not the owner of this branch'), 'error')
        return redirect(url_for('branches.clone', project=project, branch=branch))
    merge_pendencies = get_merge_pendencies(project, branch)
    if merge_pendencies:
        return pendencies
    branch_source_path = join('repos', project, branch, 'source', filename + '.rst')
    branch_html_path = join('repos', project, branch, 'build/html', filename + '.html')
    if request.method == 'POST':
        html_scroll = request.form['html_scroll']
        edit_scroll = request.form['edit_scroll']
        write_file(branch_source_path, request.form['code'])
        repo = git.Repo(join('repos', project, branch, 'source'))
        flash(_('File saved successfully'), 'info')
        repo.index.add([filename + '.rst'])
    build(project, branch)
    rst = load_file(branch_source_path)
    doc = render_template_string(load_file(branch_html_path), barebones=True)
    menu = {'right': [{'name': branch,
                       'url': url_for('branches.edit', project=project, branch=branch, filename=filename)}]}
    return render_template('edit.html', doc=doc, rst=rst, filename=filename,
                           menu=menu, html_scroll=html_scroll,
                           edit_scroll=edit_scroll, render_sidebar=False)

@limiter.limit("300 per day")
@branches.route('/html2rst', methods = ['GET', 'POST'])
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

@branches.route('/<project>/pdf')
@branches.route('/<project>/<branch>/pdf')
def pdf(project, branch='master'):
    build_path = os.path.abspath(join('repos', project, branch, 'build/latex'))
    build_latex(project, branch)
    command = '(cd ' + build_path + '; pdflatex -interaction nonstopmode linux.tex > /tmp/222 || true)'
    os.system(command)
    return flask.send_from_directory(build_path, 'linux.pdf')

@branches.route('/<project>/<branch>/view/genindex.html')
def genindex(project, branch):
    return redirect(url_for('branches.view', project=project, branch=branch, filename='index.html'))
