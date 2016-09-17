import os
import json
from os.path import join, isdir
import flask
from flask import render_template, render_template_string, request, redirect, url_for, Response, flash
from flask_user import login_required, UserManager, UserMixin, SQLAlchemyAdapter, current_user
from sphinx_edit import app
import string
from shutil import copyfile
import git

import codecs # deals with encoding better
import sphinx

config_path = 'conf'

def get_git(project, user_name):
    repo_path = join('repos', project, user_name, 'source')
    repo = git.Repo(repo_path)
    return repo.git

def is_merging(git_api):
    try:
        git_api.merge('HEAD')
    except git.GitCommandError as inst:
        return True
    return False

def get_requests(project, user_name):
    git_api = get_git(project, user_name)
    if is_merging(git_api):
        return redirect('/' + project + '/merge/someone')
    branches = string.split(git_api.branch())
    merged = string.split(git_api.branch('--merged'))
    unmerged = [item for item in branches if item not in merged]
    # ranches.remove('master')
    # ranches.remove('*')
    if len(unmerged):
        return render_template('requests.html', branches=unmerged, project=project)

def check_repo(project, user_name):
    user_repo_path = join('repos', project, user_name)
    if not isdir(user_repo_path):
        return redirect('/' + project + '/reviewer')
    else:
        requests = get_requests(project, user_name)
        if requests:
            return requests
        git_api = get_git(project, user_name)
        if user_name == get_creator(project):
            #branches = string.split(git_api.branch())
            #print()
            #print(branches)
            #print()
            #for b in branches:
            #    if b != 'master' and b != '*':
            #        git_api.merge('--no-commit', '-s', 'recursive', '-Xtheirs', b)
            print("A")
        else:
            git_api.fetch()
            git_api.merge('-s', 'recursive', '-Xours', 'origin/master')
            git_api.push('origin', user_name)




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
    config_repo(repo, user_name, 'bla@here.com')
    copyfile('sphinx_edit/empty_repo/source/index.rst', join(repo_path, 'source/index.rst'))
    copyfile('sphinx_edit/empty_repo/.gitignore', join(repo_path, 'source/.gitignore'))
    repo.index.add(['index.rst', '.gitignore'])
    repo.index.commit('Initial commit')
    properties = {'project': project, 'creator': user_name}
    with codecs.open(join('repos', project, 'properties.json'), 'w') as dest_file:
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
    # Clone repository from creator
    repo_path = join('repos', project, user_name, 'source')
    main_repo = git.Repo(join('repos', project, reviewer, 'source'))
    main_repo.clone(os.path.abspath(join(os.getcwd(), repo_path)))
    repo = git.Repo(os.path.abspath(join(os.getcwd(), repo_path)))
    config_repo(repo, user_name, 'bla@here.com')
    git_api = repo.git
    git_api.checkout('HEAD', b=user_name)
    properties = {'reviewer': reviewer}
    with codecs.open(join('repos', project, user_name, 'properties.json'), 'w') as dest_file:
        dest_file.write(json.dumps(properties))
    build(project, user_name)

# def build(source_path, target_path, conf_path, flags):
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

# def build(source_path, target_path, conf_path, flags):
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
        # if current_user.username == get_creator(project):
        #     if has_requests(get_git(project, current_user.username)):
        #         return redirect(project + '/requests')
        #     if is_merging(get_git(project, current_user.username)):
        #         return redirect(project + '/merge')
        pendencies = check_repo(project, current_user.username)
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
    if is_merging(get_git(project, current_user.username)):
        return redirect(project + 'merge')
    filename, file_extension = os.path.splitext(filename)
    user_repo_path = join('repos', project, current_user.username)
    if request.method == 'POST':
        with codecs.open(join(user_repo_path, 'source', filename + '.rst'), 'w') as dest_file:
            dest_file.write(request.form['code'].encode('utf8'))
    build(project, current_user.username)
    repo = git.Repo(join(user_repo_path, 'source'))
    repo.index.add([filename + '.rst'])
    repo.index.commit('Change in ' + filename + ' by ' + current_user.username)
    git_api = repo.git
    if not get_creator(project) == current_user.username:
        git_api.push('origin', current_user.username)
    flash('Page submitted!', 'info')
    return redirect('/' + project + '/view/' + filename)

@app.route('/<project>/edit/<path:filename>', methods = ['GET', 'POST'])
@login_required
def edit(project, filename):
    if is_merging(get_git(project, current_user.username)):
        return redirect(project + 'merge')
    user_repo_path = join('repos', project, current_user.username)
    if request.method == 'POST':
        with codecs.open(join(user_repo_path, 'source', filename + '.rst'), 'w') as dest_file:
            dest_file.write(request.form['code'].encode('utf8'))
    build(project, current_user.username)
    print(os.getcwd())
    with codecs.open(join(user_repo_path, 'source', filename + '.rst'), 'r', 'utf-8') as content_file:
        rst = content_file.read()
    with codecs.open(join(user_repo_path, 'build/html', filename + '.html'), 'r', 'utf-8') as content_file:
        doc = render_template_string(content_file.read(), barebones=True)
    return render_template('edit.html', doc=doc, rst=rst, filename=filename, reponame=project, render_sidebar=False)

@login_required
@app.route('/<project>/merge/<branch>')
def merge(project, branch):
    git_api = get_git(project, current_user.username)
    if not is_merging(git_api):
        git_api.merge('--no-commit', '--no-ff', '-s', 'recursive', '-Xtheirs', branch)
        modified = string.split(git_api.diff('HEAD', '--name-only'))
        merging = {'branch': branch, 'modified': modified}
        with codecs.open(join('repos', project, current_user.username, 'merging.json'), 'w') as dest_file:
            dest_file.write(json.dumps(merging))
    bar_menu = [{'url': '/logout', 'name': 'logout'},
                {'url': '/profile', 'name': current_user.username}]
    with codecs.open(join('repos', project, current_user.username, 'merging.json'), 'r', 'utf-8') as content_file:
        merging = json.loads(content_file.read())
    print(merging)
    return render_template('merge.html', project=project, modified=merging['modified'], branch=branch, bar_menu=bar_menu)

@app.route('/<project>/<action>/_images/<path:filename>')
@app.route('/edit/<project>/images/<path:filename>', methods = ['GET'])
def get_tikz(project, action, filename):
    images_path = join('repos', project, current_user.username, 'build/html/_images')
    return flask.send_from_directory(os.path.abspath(images_path), filename)

@app.route('/<project>/comment_summary/<path:filename>')
def comment_summary(project, filename):
    return 'Comments from ' + filename

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

@app.route('/<project>')
def index(project):
    if is_merging(get_git(project, current_user.username)):
        return redirect(project + 'merge')
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
    build_path = os.path.abspath(join('repos', project, get_creator(project), 'build/latex'))
    build_latex(project, current_user.username)
    command = '(cd ' + build_path + '; pdflatex -interaction nonstopmode linux.tex > /tmp/222 || true)'
    os.system(command)
    return flask.send_from_directory(build_path, 'linux.pdf')

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


