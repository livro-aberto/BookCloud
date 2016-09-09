import os
from os.path import join, isdir
import flask
from flask import render_template, render_template_string, request, redirect, url_for, Response, flash
from flask_user import login_required, UserManager, UserMixin, SQLAlchemyAdapter, current_user
from sphinx_edit import app

from shutil import copyfile
import git

import codecs # deals with encoding better
import sphinx

config_path = 'conf'

# def check_main():
#     # Check if the main repository has already been initiated. Otherwise, do it
#     repo_path = 'repos/aaa/main'
#     if (not os.path.isdir(repo_path)):
#         os.makedirs(repo_path)
#         git.Repo.init(repo_path)
#         repo = git.Repo(repo_path)
#         os.makedirs(join(repo_path, 'source'))
#         copyfile('sphinx_edit/empty_repo/source/index.rst', join(repo_path, 'source/index.rst'))
#         copyfile('sphinx_edit/empty_repo/.gitignore', join(repo_path, '.gitignore'))
#         repo.index.add(['source/index.rst', '.gitignore'])
#         repo.index.commit('Initial commit')
#         build(join(repo_path, 'source'), join(repo_path, 'build/html'), config_path, '')

def create_project(project, user_name):
    # create a repository
    repo_path = join('repos', project, user_name)
    os.makedirs(repo_path)
    os.makedirs(join(repo_path, 'source'))
    git.Repo.init(join(repo_path, 'source'))
    repo = git.Repo(join(repo_path, 'source'))
    copyfile('sphinx_edit/empty_repo/source/index.rst', join(repo_path, 'source/index.rst'))
    copyfile('sphinx_edit/empty_repo/.gitignore', join(repo_path, 'source/.gitignore'))
    repo.index.add(['index.rst', '.gitignore'])
    repo.index.commit('Initial commit')
    build(project, user_name)

def clone_project(project, user_name):
    # Check if the user has a repository. Otherwise, clone from main
    repo_path = join('repos', project, user_name, 'source')
    # print('\n\n' + os.getcwd() + '\n\n')
    # print('\n\n' + os.path.dirname(os.path.realpath(__file__)) + '\n\n')

    # Search for main
    main_repo = git.Repo(join('repos', project, 'main/source'))
    main_repo.clone(os.path.abspath(join(os.getcwd(), repo_path)))
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

@app.route('/test')
def test():
    with codecs.open('/home/gutosurrex/gsync/Programming/BookCloud/sphinx_edit/templates/testpage.html', 'r', 'utf-8') as content_file:
        content = content_file.read()

    return render_template_string(content, standalone=True, render_sidebar=True)

@app.route('/<project>/view/<path:filename>')
def view(project, filename):
    if (current_user.is_authenticated):
        user_repo_path = join('repos', project, current_user.username)
        if not isdir(user_repo_path):
            clone_project(project, current_user.username)
            flash('Project cloned successfully', 'info')
        bar_menu = [{'url': '/logout', 'name': 'logout'},
                    {'url': '/' + project + '/edit/' + filename, 'name': 'edit'},
                    {'url': '/profile', 'name': current_user.username}]
    else:
        user_repo_path = join('repos', project, 'main')
        bar_menu = [{'url': '/login', 'name': 'login'},
                    {'url': '/profile', 'name': current_user.username}]
    filename, file_extension = os.path.splitext(filename)
    if file_extension == '':
        file_extension = '.html'
    with codecs.open(join(user_repo_path, 'build/html', filename + file_extension), 'r', 'utf-8') as content_file:
        content = content_file.read()
    return render_template_string(content, reponame=project, bar_menu=bar_menu, render_sidebar=True)

@app.route('/<project>/save/<path:filename>', methods = ['GET', 'POST'])
@login_required
def save(project, filename):
    user_repo_path = join('repos', project, current_user.username)
    file = join('source', filename + '.rst')
    if request.method == 'POST':
        with codecs.open(join(user_repo_path, filename), 'w') as dest_file:
            dest_file.write(request.form['code'].encode('utf8'))
    repo = git.Repo(join(user_repo_path, 'source'))
    print(filename)
    repo.index.add([filename + '.rst'])
    repo.index.commit('Change in ' + filename + ' by ' + current_user.username)
    build(project, current_user.username)
    flash('Page submitted!', 'info')
    return redirect('/' + project + '/view/' + filename)

@app.route('/<project>/edit/<path:filename>', methods = ['GET', 'POST'])
@login_required
def edit(project, filename):
    filename, file_extension = os.path.splitext(filename)
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

@app.route('/<project>/<action>/_images/<path:filename>', methods = ['GET'])
@app.route('/edit/<project>/images/<path:filename>', methods = ['GET'])
def get_tikz(project, action, filename):
    images_path = join('repos', project, 'main/build/html/_images')
    return flask.send_from_directory(os.path.abspath(images_path), filename)

@app.route('/<project>/comment_summary/<path:filename>')
def comment_summary(project, filename):
    return 'Comments from ' + filename

@app.route('/<project>/<action>/_static/<path:filename>')
def get_static(project, action, filename):
    if (current_user.is_authenticated):
        user_repo_path = join('repos', project, current_user.username)
    else:
        user_repo_path = join('repos', project, 'main')
    return flask.send_from_directory(os.path.abspath(join(user_repo_path, 'build/html/_static/')), filename)

@app.route('/_static/<path:filename>')
def get_global_static(filename):
    return flask.send_from_directory(os.path.abspath('conf/biz/static/'), filename)

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
    build_path = os.path.abspath(join('repos', project, 'main', 'build/latex'))
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
