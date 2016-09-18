import os
import json
from os.path import join, isdir, isfile
import flask
from flask import render_template, render_template_string, request, redirect, url_for, Response, flash
from flask_user import login_required, UserManager, UserMixin, SQLAlchemyAdapter, current_user
from sphinx_edit import app
import string
from shutil import copyfile
import git
from difflib import HtmlDiff

import codecs # deals with encoding better
import sphinx

config_path = 'conf'

def get_git(project, user_name):
    repo_path = join('repos', project, user_name, 'source')
    repo = git.Repo(repo_path)
    return repo.git

def get_merging(project, user_name):
    merge_file_path = join('repos', project, user_name, 'merging.json')
    if isfile(merge_file_path):
        with codecs.open(merge_file_path, 'r', 'utf-8') as content_file:
            return json.loads(content_file.read())

def get_requests(project, user_name):
    git_api = get_git(project, user_name)
    branches = string.split(git_api.branch())
    merged = string.split(git_api.branch('--merged'))
    unmerged = [item for item in branches if item not in merged]
    bar_menu = [{'url': '/logout', 'name': 'logout'},
                {'url': '/profile', 'name': current_user.username}]
    if len(unmerged):
        return render_template('requests.html', branches=unmerged, project=project, bar_menu=bar_menu)

def get_pendencies(project, user_name):
    # user already has the repository?
    user_repo_path = join('repos', project, user_name)
    if not isdir(user_repo_path):
        return redirect('/' + project + '/reviewer')
    # user is merging?
    merging = get_merging(project, user_name)
    if merging:
        return redirect('/' + project + '/merge/' + merging['branch'])
    # user has a pending request?
    requests = get_requests(project, user_name)
    if requests:
        return requests
    # update from reviewer (if the user is not his own reviewer)
    if not user_name == get_reviewer(project, user_name):
        git_api = get_git(project, user_name)
        git_api.fetch()
        git_api.merge('-s', 'recursive', '-Xours', 'origin/master')
        git_api.push('origin', user_name)
        build(project, user_name)

def config_repo(repo, user_name, email):
    config = repo.config_writer()
    config.set_value('user', 'email', email)
    config.set_value('user', 'name', user_name)

def create_project(project, user_name):
    # create a repository
    repo_path = join('repos', project, user_name)
    os.makedirs(repo_path)
    os.makedirs(join(repo_path, 'source'))
    git.Repo.init(join(repo_path, 'source'))
    repo = git.Repo(join(repo_path, 'source'))
    config_repo(repo, user_name, user_name + '@example.com')
    copyfile('sphinx_edit/empty_repo/source/index.rst', join(repo_path, 'source/index.rst'))
    copyfile('sphinx_edit/empty_repo/.gitignore', join(repo_path, 'source/.gitignore'))
    repo.index.add(['index.rst', '.gitignore'])
    repo.index.commit('Initial commit')
    properties = {'project': project, 'creator': user_name}
    with codecs.open(join('repos', project, 'properties.json'), 'w') as dest_file:
        dest_file.write(json.dumps(properties))
    properties = {'reviewer': user_name}
    with codecs.open(join('repos', project, user_name, 'properties.json'), 'w') as dest_file:
        dest_file.write(json.dumps(properties))
    build(project, user_name)

def get_creator(project):
    with codecs.open(join('repos', project, 'properties.json'), 'r', 'utf-8') as content_file:
        properties = json.loads(content_file.read())
        return properties['creator']

def get_reviewer(project, user_name):
    with codecs.open(join('repos', project, user_name, 'properties.json'), 'r', 'utf-8') as content_file:
        properties = json.loads(content_file.read())
        return properties['reviewer']

def clone_project(project, user_name, reviewer):
    # Clone repository from a reviewer
    repo_path = join('repos', project, user_name, 'source')
    main_repo = git.Repo(join('repos', project, reviewer, 'source'))
    main_repo.clone(os.path.abspath(join(os.getcwd(), repo_path)))
    repo = git.Repo(os.path.abspath(join(os.getcwd(), repo_path)))
    config_repo(repo, user_name, user_name + '@here.com')
    git_api = repo.git
    git_api.checkout('HEAD', b=user_name)
    properties = {'reviewer': reviewer}
    with codecs.open(join('repos', project, user_name, 'properties.json'), 'w') as dest_file:
        dest_file.write(json.dumps(properties))
    build(project, user_name)

def build(project, user):
    # Replace this terrible implementation
    config_path = 'conf'
    source_path = join('repos', project, user, 'source')
    build_path = join('repos', project, user, 'build/html')
    # args = ['-a', '-c conf']
    # if sphinx.build_main(args + ['source/', 'build/html/']):
    #     os.chdir(previous_wd)
    #     return False
    # os.chdir(previous_wd)
    # return True
    command = 'sphinx-build -a -c ' + config_path + ' ' + source_path + ' ' + build_path
    os.system(command)
    return True

def build_latex(project, user):
    # Replace this terrible implementation
    config_path = 'conf'
    source_path = join('repos', project, user, 'source')
    build_path = join('repos', project, user, 'build/latex')
    command = 'sphinx-build -a -b latex -c ' + config_path + ' ' + source_path + ' ' + build_path
    os.system(command)
    return True

@login_required
@app.route('/<project>/reviewer')
def reviewer(project):
    path = 'repos/' + project
    reviewers = [d for d in os.listdir(path) if isdir(join(path, d))]
    bar_menu = [{'url': '/logout', 'name': 'logout'},
                {'url': '/profile', 'name': current_user.username}]
    return render_template('reviewer.html', reviewers=reviewers, project=project, bar_menu=bar_menu)

@login_required
@app.route('/<project>/accept/<path:filename>')
def accpet(project, filename):
    merging = get_merging(project, current_user.username)
    if not merging:
        flash('You are not merging a submission', 'error')
        return redirect('/' + project)
    if not filename in merging['modified']:
        flash('File ' + filename + ' was not being reviewed', 'error')
        return redirect('/' + project)
    merging['modified'].remove(filename)
    merging['reviewed'].append(filename)
    merge_file_path = join('repos', project, current_user.username, 'merging.json')
    with codecs.open(merge_file_path, 'w') as dest_file:
        dest_file.write(json.dumps(merging))
    return redirect('/' + project + '/merge/' + merging['branch'])

@login_required
@app.route('/<project>/finish')
def finish(project):
    merging = get_merging(project, current_user.username)
    if not merging:
        flash('You are not merging!', 'error')
        return redirect(url_for('/' + project))
    if len(merging['modified']):
        flash('You still have unreviewed files', 'error')
        return redirect('/' + project)
    git_api = get_git(project, current_user.username)
    git_api.commit('-m', 'Merge ' + merging['branch'])
    merge_file_path = join('repos', project, current_user.username, 'merging.json')
    os.remove(merge_file_path)
    build(project, current_user.username)
    return redirect('/' + project)

@login_required
@app.route('/<project>/clone/<reviewer>')
def clone(project, reviewer):
    clone_project(project, current_user.username, reviewer)
    flash('Project cloned successfully!', 'info')
    return redirect('/' + project)

@app.route('/<project>/view/<path:filename>')
def view(project, filename):
    filename, file_extension = os.path.splitext(filename)
    if (current_user.is_authenticated):
        user_repo_path = join('repos', project, current_user.username)
        pendencies = get_pendencies(project, current_user.username)
        if pendencies:
            return pendencies
        bar_menu = [{'url': '/logout', 'name': 'logout'},
                    {'url': '/' + project + '/edit/' + filename, 'name': 'edit'},
                    {'url': '/profile', 'name': current_user.username}]
    else:
        creator = get_creator(project)
        user_repo_path = join('repos', project, creator)
        bar_menu = [{'url': '/login', 'name': 'login'}]
    filename, file_extension = os.path.splitext(filename)
    if file_extension == '':
        file_extension = '.html'
    with codecs.open(join(user_repo_path, 'build/html', filename + file_extension), 'r', 'utf-8') as content_file:
        content = content_file.read()
    return render_template_string(content, reponame=project, bar_menu=bar_menu, render_sidebar=True)

@app.route('/<project>/save/<path:filename>', methods = ['GET', 'POST'])
@login_required
def save(project, filename):
    pendencies = get_pendencies(project, current_user.username)
    if pendencies:
        return pendencies
    filename, file_extension = os.path.splitext(filename)
    user_repo_path = join('repos', project, current_user.username)
    if request.method == 'POST':
        with codecs.open(join(user_repo_path, 'source', filename + '.rst'), 'w') as dest_file:
            dest_file.write(request.form['code'].encode('utf8'))
    repo = git.Repo(join(user_repo_path, 'source'))
    repo.index.add([filename + '.rst'])
    repo.index.commit('Change in ' + filename + ' by ' + current_user.username)
    git_api = repo.git
    if current_user.username != get_reviewer(project, current_user.username):
        git_api.push('origin', current_user.username)
    flash('Page submitted!', 'info')
    build(project, current_user.username)
    return redirect('/' + project + '/view/' + filename)

@app.route('/<project>/edit/<path:filename>', methods = ['GET', 'POST'])
@login_required
def edit(project, filename):
    pendencies = get_pendencies(project, current_user.username)
    if pendencies:
        return pendencies
    user_repo_path = join('repos', project, current_user.username)
    if request.method == 'POST':
        with codecs.open(join(user_repo_path, 'source', filename + '.rst'), 'w') as dest_file:
            dest_file.write(request.form['code'].encode('utf8'))
    build(project, current_user.username)
    with codecs.open(join(user_repo_path, 'source', filename + '.rst'), 'r', 'utf-8') as content_file:
        rst = content_file.read()
    with codecs.open(join(user_repo_path, 'build/html', filename + '.html'), 'r', 'utf-8') as content_file:
        doc = render_template_string(content_file.read(), barebones=True)
    return render_template('edit.html', doc=doc, rst=rst, filename=filename,
                           reponame=project, render_sidebar=False)

@login_required
@app.route('/<project>/diff/<path:filename>')
def diff(project, filename):
    merging = get_merging(project, current_user.username)
    if not merging:
        flash('You are not merging!', 'error')
        return redirect(url_for('/' + project))
    bar_menu = [{'url': '/logout', 'name': 'logout'},
                {'url': '/profile', 'name': current_user.username}]
    differ = HtmlDiff()
    user_repo_path = join('repos', project, current_user.username)
    filename, file_extension = os.path.splitext(filename)
    with codecs.open(join(user_repo_path, 'source', filename + '.rst'), 'r', 'utf-8') as content_file:
        rst = string.split(content_file.read(), '\n')
    git_api = get_git(project, current_user.username)
    old = string.split(git_api.show('master:' + filename + file_extension), '\n')
    diff = differ.make_table(rst, old)
    return render_template('diff.html', branch=merging['branch'], project=project,
                           diff=diff, filename=filename + file_extension, bar_menu=bar_menu)

@login_required
@app.route('/<project>/merge/<branch>')
def merge(project, branch):
    merging = get_merging(project, current_user.username)
    if not merging:
        git_api = get_git(project, current_user.username)
        git_api.merge('--no-commit', '--no-ff', '-s', 'recursive', '-Xtheirs', branch)
        modified = string.split(git_api.diff('HEAD', '--name-only'))
        merging = {'branch': branch, 'modified': modified, 'reviewed': []}
        with codecs.open(join('repos', project, current_user.username, 'merging.json'), 'w') as dest_file:
            dest_file.write(json.dumps(merging))
    bar_menu = [{'url': '/logout', 'name': 'logout'},
                {'url': '/profile', 'name': current_user.username}]
    return render_template('merge.html', project=project, modified=merging['modified'],
                           reviewed=merging['reviewed'], branch=branch, bar_menu=bar_menu)

@app.route('/<project>')
def index(project):
    return redirect(project + '/view/index')

@app.route('/')
def projects():
    path = 'repos'
    projects = [d for d in os.listdir(path) if isdir(join(path, d))]
    if current_user.is_authenticated:
        bar_menu = [{'url': '/logout', 'name': 'logout'},
                    {'url': '/profile', 'name': current_user.username}]
    else:
        bar_menu = [{'url': '/login', 'name': 'login'}]
    return render_template('projects.html', projects=projects, bar_menu=bar_menu, copyright='CC-BY-SA-NC')

@app.route('/profile')
def profile():
    if not current_user.is_authenticated:
        redirect (url_for('login'))
    bar_menu = [{'url': '/logout', 'name': 'logout'},
                {'url': '/', 'name': 'home'},
                {'url': '/profile', 'name': current_user.username}]
    return render_template('profile.html', username=current_user.username, bar_menu=bar_menu)

@app.route('/new', methods = ['GET', 'POST'])
def new():
    if not current_user.is_authenticated:
        flash('You need to be logged in to create a new project', 'error')
        return redirect(url_for('login'))
    bar_menu = [{'url': '/logout', 'name': 'logout'},
                {'url': '/', 'name': 'home'},
                {'url': '/profile', 'name': current_user.username}]
    if request.method == 'POST':
        repo_path = join('repos', request.form['project'], current_user.username)
        if os.path.isdir(repo_path):
            flash('This project name already exists', 'error')
            return render_template('new.html', username=current_user.username, bar_menu=bar_menu)
        else:
            create_project(request.form['project'], current_user.username)
            flash('Project created successfuly!', 'info')
            return redirect('/')
    return render_template('new.html', username=current_user.username, bar_menu=bar_menu)

@app.route('/<project>/pdf')
def pdf(project):
    if (current_user.is_authenticated):
        build_path = os.path.abspath(join('repos', project, current_user.username, 'build/latex'))
    else:
        build_path = os.path.abspath(join('repos', project, get_creator(project), 'build/latex'))
    build_latex(project, current_user.username)
    command = '(cd ' + build_path + '; pdflatex -interaction nonstopmode linux.tex > /tmp/222 || true)'
    os.system(command)
    return flask.send_from_directory(build_path, 'linux.pdf')

@app.route('/<project>/comment_summary/<path:filename>')
def comment_summary(project, filename):
    return 'Comments from ' + filename

@app.route('/<project>/<action>/_images/<path:filename>')
@app.route('/edit/<project>/images/<path:filename>', methods = ['GET'])
def get_tikz(project, action, filename):
    images_path = join('repos', project, current_user.username, 'build/html/_images')
    return flask.send_from_directory(os.path.abspath(images_path), filename)

@app.route('/<project>/<action>/_static/<path:filename>')
def get_static(project, action, filename):
    if (current_user.is_authenticated):
        user_repo_path = join('repos', project, current_user.username)
    else:
        user_repo_path = join('repos', project, get_creator(project))
    return flask.send_from_directory(os.path.abspath(join(user_repo_path, 'build/html/_static/')), filename)

@app.route('/_static/<path:filename>')
def get_global_static(filename):
    return flask.send_from_directory(os.path.abspath('conf/biz/static/'), filename)

@app.route('/_sources/<path:filename>')
def show_source(filename):
    user_repo_path = join('repos', current_user.username)
    with codecs.open(join(user_repo_path, 'build/html/_sources', filename), 'r', 'utf-8') as content_file:
        content = content_file.read()
    return Response(content, mimetype='text/txt')

@app.route('/<project>/images/<path:filename>')
def get_image(project, filename):
    return flask.send_from_directory(os.path.abspath('repos/' + project + '/images'), filename)

@app.route('/<project>/view/genindex.html')
def genindex(project):
    return redirect('/' + project + '/view/index')

@app.route('/login')
def login():
    return redirect(url_for('user.login'))

@app.route('/logout')
def logout():
    return redirect(url_for('user.logout'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# @app.errorhandler(403)
# def page_forbidden(e):
#     return render_template('403.html'), 500


