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

def load_json(path):
    with codecs.open(path, 'r', 'utf-8') as content_file:
        return json.loads(content_file.read())

def write_json(path, structure):
    with codecs.open(path, 'w', 'utf-8') as dest_file:
        dest_file.write(json.dumps(structure))

def get_merging(project, user_name):
    merge_file_path = join('repos', project, user_name, 'merging.json')
    if isfile(merge_file_path):
        return load_json(merge_file_path)

def std_menu(username):
    return [{'url': '/logout', 'name': 'logout'},
            {'url': '/profile', 'name': username}]

def get_requests(project, user_name):
    git_api = get_git(project, user_name)
    branches = string.split(git_api.branch())
    merged = string.split(git_api.branch('--merged'))
    unmerged = [item for item in branches if item not in merged]
    bar_menu = std_menu(current_user.username)
    if len(unmerged):
        return render_template('requests.html', project=project, unmerged=unmerged, bar_menu=bar_menu)

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
    write_json(join('repos', project, 'properties.json'), properties)
    properties = {'reviewer': user_name}
    write_json(join('repos', project, user_name, 'properties.json'), properties)
    build(project, user_name)

def get_creator(project):
    properties = load_json(join('repos', project, 'properties.json'))
    return properties['creator']

def get_reviewer(project, user_name):
    properties = load_json(join('repos', project, user_name, 'properties.json'))
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
    write_json(join('repos', project, user_name, 'properties.json'), properties)
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
    path = join('repos', project)
    reviewers = [d for d in os.listdir(path) if isdir(join(path, d))]
    bar_menu = std_menu(current_user.username)
    text = {'title': 'Clone project', 'headline': 'Choose your reviewer'}
    return render_template('reviewer.html', project=project, reviewers=reviewers,
                           text=text, bar_menu=bar_menu)

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
    write_json(merge_file_path, merging)
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
    if file_extension == '':
        file_extension = '.html'
    if (current_user.is_authenticated):
        user_repo_path = join('repos', project, current_user.username,
                              'build/html', filename + file_extension)
        pendencies = get_pendencies(project, current_user.username)
        if pendencies:
            return pendencies
        bar_menu = [{'url': '/logout', 'name': 'logout'},
                    {'url': '/' + project + '/edit/' + filename, 'name': 'edit'},
                    {'url': '/profile', 'name': current_user.username}]
    else:
        creator = get_creator(project)
        user_repo_path = join('repos', project, creator,
                              'build/html', filename + file_extension)
        bar_menu = [{'url': '/login', 'name': 'login'}]
    build(project, current_user.username)
    with codecs.open(user_repo_path, 'r', 'utf-8') as content_file:
        content = content_file.read()
    return render_template_string(content, bar_menu=bar_menu, render_sidebar=True)

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
    reviewer = get_reviewer(project, current_user.username)
    if current_user.username != reviewer:
        git_api.push('origin', current_user.username)
    flash('Page submitted to @' + reviewer, 'info')
    build(project, current_user.username)
    return redirect('/' + project + '/view/' + filename)

@app.route('/<project>/edit/<path:filename>', methods = ['GET', 'POST'])
@login_required
def edit(project, filename):
    pendencies = get_pendencies(project, current_user.username)
    if pendencies:
        return pendencies
    user_source_path = join('repos', project, current_user.username, 'source', filename + '.rst')
    user_html_path = join('repos', project, current_user.username, 'build/html', filename + '.html')
    if request.method == 'POST':
        with codecs.open(user_source_path, 'w') as dest_file:
            dest_file.write(request.form['code'].encode('utf8'))
    build(project, current_user.username)
    with codecs.open(user_source_path, 'r', 'utf-8') as content_file:
        rst = content_file.read()
    with codecs.open(user_html_path, 'r', 'utf-8') as content_file:
        doc = render_template_string(content_file.read(), barebones=True)
    text = {'title': 'Edit:', 'image': 'Image', 'math': 'Math mode',
            'sections': 'Sections', 'style': 'Style',
            'cancel': 'Cancel', 'preview': 'Preview', 'submit': 'Submit'}
    return render_template('edit.html', doc=doc, rst=rst, filename=filename,
                           project=project, text=text, render_sidebar=False)

@login_required
@app.route('/<project>/diff/<path:filename>')
def diff(project, filename):
    merging = get_merging(project, current_user.username)
    if not merging:
        flash('You are not merging!', 'error')
        return redirect(url_for('/' + project))
    bar_menu = std_menu(current_user.username)
    differ = HtmlDiff()
    filename, file_extension = os.path.splitext(filename)
    user_source_path = join('repos', project, current_user.username, 'source', filename + '.rst')
    with codecs.open(user_source_path, 'r', 'utf-8') as content_file:
        new = string.split(content_file.read(), '\n')
    git_api = get_git(project, current_user.username)
    old = string.split(git_api.show('master:' + filename + file_extension), '\n')
    diff = differ.make_table(new, old)
    diff = string.replace(diff, 'nowrap="nowrap"', '')
    text = {'title': ' has suggested a change to the file: ',
            'instructions': 'The proposed version is on the left, while the old version is on the right.'}
    return render_template('diff.html',  project=project, branch=merging['branch'],
                           diff=diff, filename=filename + file_extension,
                           text=text, bar_menu=bar_menu)

@login_required
@app.route('/<project>/merge/<branch>')
def merge(project, branch):
    merging = get_merging(project, current_user.username)
    if not merging:
        git_api = get_git(project, current_user.username)
        git_api.merge('--no-commit', '--no-ff', '-s', 'recursive', '-Xtheirs', branch)
        modified = string.split(git_api.diff('HEAD', '--name-only'))
        merging = {'branch': branch, 'modified': modified, 'reviewed': []}
        write_json(join('repos', project, current_user.username, 'merging.json'), merging)
    bar_menu = std_menu(current_user.username)
    text = {'title': 'Merging from @', 'unseen': 'Modifications not yet reviewed',
            'review': 'Review file', 'accept': 'Accept suggestions', 'view': 'View differences',
            'reviewed': 'Changes reviewed', 'finally': 'You have finished all the reviews',
            'finish': 'Finish merge'}
    return render_template('merge.html', project=project, modified=merging['modified'],
                           reviewed=merging['reviewed'], branch=branch,
                           text=text, bar_menu=bar_menu)

@app.route('/<project>')
def index(project):
    return redirect(project + '/view/index')

@app.route('/')
def projects():
    path = 'repos'
    projects = [d for d in os.listdir(path) if isdir(join(path, d))]
    if current_user.is_authenticated:
        bar_menu = std_menu(current_user.username)
    else:
        bar_menu = [{'url': '/login', 'name': 'login'}]
    text = {'title': 'Projects list', 'download': 'Download', 'new': 'Create new project'}
    return render_template('projects.html', projects=projects, bar_menu=bar_menu,
                           text=text, copyright='CC-BY-SA-NC')

@app.route('/profile')
def profile():
    if not current_user.is_authenticated:
        redirect (url_for('login'))
    bar_menu = std_menu(current_user.username)
    return render_template('profile.html', username=current_user.username, bar_menu=bar_menu)

@app.route('/new', methods = ['GET', 'POST'])
def new():
    if not current_user.is_authenticated:
        flash('You need to be logged in to create a new project', 'error')
        return redirect(url_for('login'))
    bar_menu = std_menu(current_user.username)
    if request.method == 'POST':
        user_repo_path = join('repos', request.form['project'], current_user.username)
        if os.path.isdir(user_repo_path):
            flash('This project name already exists', 'error')
            return render_template('new.html', username=current_user.username, bar_menu=bar_menu)
        else:
            create_project(request.form['project'], current_user.username)
            flash('Project created successfuly!', 'info')
            return redirect('/')
    text = {'title': 'Create new project', 'submit': 'Submit'}
    return render_template('new.html', username=current_user.username,
                           text=text, bar_menu=bar_menu)

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
    sources_path = join('repos', current_user.username, 'build/html/_sources', filename)
    with codecs.open(sources_path, 'r', 'utf-8') as content_file:
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


