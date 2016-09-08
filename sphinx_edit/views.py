import os
from os.path import join, isdir
import flask
from flask import render_template, render_template_string, request, redirect, url_for, Response
from flask_user import login_required, UserManager, UserMixin, SQLAlchemyAdapter, current_user
from sphinx_edit import app

from shutil import copyfile
import git

import codecs # deals with encoding better
import sphinx

config_path = 'conf'

def check_main():
    # Check if the main repository has already been initiated. Otherwise, do it
    repo_path = 'repos/aaa/main'
    if (not os.path.isdir(repo_path)):
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

@app.route('/aaa/view/<path:filename>')
def view(filename):
    # Think if this should really be from the user
    check_main()
    if (current_user.is_authenticated):
        user_repo_path = join('repos/aaa', current_user.username)
        check_user(current_user.username)
    else:
        user_repo_path = join('repos/aaa', 'main')
    filename, file_extension = os.path.splitext(filename)
    if file_extension == "":
        file_extension = '.html'
    with codecs.open(join(user_repo_path, 'build/html', filename + file_extension), 'r', 'utf-8') as content_file:
        content = content_file.read()

    return render_template_string(content, content=content, standalone=True, render_sidebar=True, reponame='aaa')

@app.route('/aaa/save/<path:filename>', methods = ['GET', 'POST'])
@login_required
def save(filename):
    user_repo_path = join('repos/aaa', current_user.username)
    if request.method == 'POST':
        with codecs.open(join(user_repo_path, 'source', filename + '.rst'), 'w') as dest_file:
            dest_file.write(request.form['code'].encode('utf8'))
    build(join(user_repo_path, 'source'), join(user_repo_path, 'build/html'), config_path, '')
    # return "Saved"
    return redirect('/aaa/view/' + filename)

@app.route('/aaa/edit/<path:filename>', methods = ['GET', 'POST'])
@login_required
def edit(filename):
    filename, file_extension = os.path.splitext(filename)
    user_repo_path = join('repos/aaa', current_user.username)
    if request.method == 'POST':
        with codecs.open(join(user_repo_path, 'source', filename + '.rst'), 'w') as dest_file:
            dest_file.write(request.form['code'].encode('utf8'))
    build(join(user_repo_path, 'source'), join(user_repo_path, 'build/html'), config_path, '')

    with codecs.open(join(user_repo_path, 'source', filename + '.rst'), 'r', 'utf-8') as content_file:
        rst = content_file.read()
    with codecs.open(join(user_repo_path, 'build/html', filename + '.html'), 'r', 'utf-8') as content_file:
        doc = render_template_string(content_file.read(), standalone=False, render_sidebar=False)
    return render_template('edit.html', doc=doc, rst=rst, filename=filename, reponame='aaa')

@app.route('/aaa/_images/<path:filename>', methods = ['GET'])
@app.route('/edit/aaa/_images/<path:filename>', methods = ['GET'])
def get_tikz(filename):
    # Think if this should really be from the user
    user_repo_path = join('repos/aaa', current_user.username)
    return flask.send_from_directory(os.path.abspath(user_repo_path + '/build/html/_images/'), filename)

@app.route('/comment_summary/aaa/<path:filename>')
def comment_summary(filename):
    return "Comments from " + filename

@app.route('/aaa/<action>/_static/<path:filename>')
def get_static(filename, action):
    if (current_user.is_authenticated):
        user_repo_path = join('repos/aaa', current_user.username)
    else:
        user_repo_path = join('repos/aaa', 'main')
    return flask.send_from_directory(os.path.abspath(join(user_repo_path, 'build/html/_static/')), filename)

@app.route('/aaa')
def index():
    return redirect('aaa/index')

@app.route('/')
def view_projects():
    path = 'repos'
    projects = [d for d in os.listdir(path) if isdir(join(path, d))]
    return render_template('projects.html', projects=projects)

@app.route('/_sources/<path:filename>')
def show_source(filename):
    # Think if this should really be from the user
    user_repo_path = join('repos', current_user.username)
    with codecs.open(join(user_repo_path, 'build/html/_sources', filename), 'r', 'utf-8') as content_file:
        content = content_file.read()
    return Response(content, mimetype='text/txt')

@app.route('/aaa/images/<path:filename>')
def get_image(filename):
    return flask.send_from_directory(os.path.abspath('repos/aaa/images'), filename)

@app.route('/genindex.html')
def genindex():
    return redirect(url_for('index'))

@app.route('/login')
def login():
    return redirect(url_for('user.login'))

@app.route('/logout')
def logout():
    return redirect(url_for('user.logout'))
