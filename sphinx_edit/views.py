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

def create_project(project_name, user_name):
    # Check if the main repository has already been initiated. Otherwise, do it
    repo_path = join('repos', project_name, user_name)
    if os.path.isdir(repo_path):
        return
    else:
        os.makedirs(repo_path)
        git.Repo.init(repo_path)
        repo = git.Repo(repo_path)
        os.makedirs(join(repo_path, 'source'))
        copyfile('sphinx_edit/empty_repo/source/index.rst', join(repo_path, 'source/index.rst'))
        copyfile('sphinx_edit/empty_repo/.gitignore', join(repo_path, '.gitignore'))
        repo.index.add(['source/index.rst', '.gitignore'])
        repo.index.commit('Initial commit')
        build(join(repo_path, 'source'), join(repo_path, 'build/html'), config_path, '')

def check_user(username):
    # Check if the user has a repository. Otherwise, clone from main
    repo_path = join('repos/aaa', username)
    if (not os.path.isdir(repo_path)):
        check_main()
        print('\n\n' + os.getcwd() + '\n\n')
        print('\n\n' + os.path.dirname(os.path.realpath(__file__)) + '\n\n')
        main_repo = git.Repo('repos/aaa/main')
        main_repo.clone(os.path.abspath(join(os.getcwd(), repo_path)))
        build(join(repo_path, 'source'), join(repo_path, 'build/html'), config_path, '')

def build(source_path, target_path, conf_path, flags):
    # Replace this terrible implementation
    command = "sphinx-build -a -c " + conf_path + " " + source_path + " " + target_path + " "
    os.system(command)
    return True
    # args = ['-a', '-c ' + conf_path]
    # if len(flags):
    #     args = args + flags
    # if sphinx.build_main(args + [source_path, target_path]):
    #     return False
    # return True

@app.route('/test')
def test():
    with codecs.open('/home/gutosurrex/gsync/Programming/BookCloud/sphinx_edit/templates/testpage.html', 'r', 'utf-8') as content_file:
        content = content_file.read()

    return render_template_string(content, standalone=True, render_sidebar=True)

@app.route('/<project>/view/<path:filename>')
def view(project, filename):
    # Think if this should really be from the user
    # check_main()
    if (current_user.is_authenticated):
        user_repo_path = join('repos', project, current_user.username)
        check_user(current_user.username)
    else:
        user_repo_path = join('repos', project, 'main')
    filename, file_extension = os.path.splitext(filename)
    if file_extension == "":
        file_extension = '.html'
    with codecs.open(join(user_repo_path, 'build/html', filename + file_extension), 'r', 'utf-8') as content_file:
        content = content_file.read()

    return render_template_string(content, content=content, reponame=project)

@app.route('/<project>/save/<path:filename>', methods = ['GET', 'POST'])
@login_required
def save(project, filename):
    user_repo_path = join('repos', project, current_user.username)
    if request.method == 'POST':
        with codecs.open(join(user_repo_path, 'source', filename + '.rst'), 'w') as dest_file:
            dest_file.write(request.form['code'].encode('utf8'))
    build(join(user_repo_path, 'source'), join(user_repo_path, 'build/html'), config_path, '')
    # return "Saved"
    return redirect('/' + project + '/view/' + filename)

@app.route('/<project>/edit/<path:filename>', methods = ['GET', 'POST'])
@login_required
def edit(project, filename):
    filename, file_extension = os.path.splitext(filename)
    user_repo_path = join('repos', project, current_user.username)
    if request.method == 'POST':
        with codecs.open(join(user_repo_path, 'source', filename + '.rst'), 'w') as dest_file:
            dest_file.write(request.form['code'].encode('utf8'))
    build(join(user_repo_path, 'source'), join(user_repo_path, 'build/html'), config_path, '')

    with codecs.open(join(user_repo_path, 'source', filename + '.rst'), 'r', 'utf-8') as content_file:
        rst = content_file.read()
    with codecs.open(join(user_repo_path, 'build/html', filename + '.html'), 'r', 'utf-8') as content_file:
        doc = render_template_string(content_file.read(), barebones=True)
    return render_template('edit.html', doc=doc, rst=rst, filename=filename, reponame=project, render_sidebar=False)

@app.route('/<project>/_images/<path:filename>', methods = ['GET'])
@app.route('/edit/<project>/_images/<path:filename>', methods = ['GET'])
def get_tikz(project, filename):
    # Think if this should really be from the user
    user_repo_path = join('repos', project, current_user.username)
    return flask.send_from_directory(os.path.abspath(user_repo_path + '/build/html/_images/'), filename)

@app.route('/<project>/comment_summary/<path:filename>')
def comment_summary(project, filename):
    return "Comments from " + filename

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
    return render_template('projects.html', projects=projects, bar_menu=bar_menu, copyright="CC-BY-SA-NC")

@app.route('/profile')
def profile():
    if not current_user.is_authenticated:
        redirect (url_for('login'))
    bar_menu = [{'url': '/logout', 'name': 'logout'},
                {'url': '/', 'name': 'home'}]
    return render_template('profile.html', username=current_user.username, bar_menu=bar_menu)

@app.route('/new', methods = ['GET', 'POST'])
def new():
    if not current_user.is_authenticated:
        flash("You need to be logged in to create a new project")
        return redirect (url_for('login'))
    bar_menu = [{'url': '/logout', 'name': 'logout'},
                {'url': '/', 'name': 'home'}]
    if request.method == 'POST':
        create_project(request.form['project'], current_user.username)
        return redirect('/')
    return render_template('new.html', username=current_user.username, bar_menu=bar_menu)

@app.route('/_sources/<path:filename>')
def show_source(filename):
    # Think if this should really be from the user
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
