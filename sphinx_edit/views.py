import os
from os.path import join
import flask
from flask import render_template, render_template_string, request, redirect, url_for, Response
from flask_user import login_required, UserManager, UserMixin, SQLAlchemyAdapter, current_user
from sphinx_edit import app

import codecs # deals with encoding better
import sphinx

user_repo_path = 'repos/bla'
config_path = 'conf'

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

@app.route('/save/<filename>', methods = ['GET', 'POST'])
@login_required
def save(filename):
    if request.method == 'POST':
        with codecs.open(join(user_repo_path, 'source', filename + '.rst'), 'w') as dest_file:
            dest_file.write(request.form['code'].encode('utf8'))
    build(join(user_repo_path, 'source'), join(user_repo_path, 'build/html'), config_path, '')
    # return "Saved"
    return redirect(filename)

@app.route('/edit/<filename>', methods = ['GET', 'POST'])
@login_required
def edit(filename):
    filename, file_extension = os.path.splitext(filename)
    if request.method == 'POST':
        with codecs.open(join(user_repo_path, 'source', filename + '.rst'), 'w') as dest_file:
            dest_file.write(request.form['code'].encode('utf8'))
    build(join(user_repo_path, 'source'), join(user_repo_path, 'build/html'), config_path, '')

    with codecs.open(join(user_repo_path, 'source', filename + '.rst'), 'r', 'utf-8') as content_file:
        rst = content_file.read()
    with codecs.open(join(user_repo_path, 'build/html', filename + '.html'), 'r', 'utf-8') as content_file:
        doc = render_template_string(content_file.read(), standalone=False, render_sidebar=False)
    return render_template('edit.html', doc=doc, rst=rst, filename=filename)

@app.route('/_images/<filename>', methods = ['GET'])
@app.route('/edit/_images/<filename>', methods = ['GET'])
def get_tikz(filename):
    return flask.send_from_directory(os.path.abspath(user_repo_path + '/build/html/_images/'), filename)

@app.route('/comment_summary/<filename>')
def comment_summary(filename):
    return "Comments from " + filename

@app.route('/_static/<filename>')
def get_static(filename):
    return flask.send_from_directory(os.path.abspath('sphinx_edit/static/sphinx_static/'), filename)

@app.route('/')
def index():
    return redirect('index')

@app.route('/_sources/<filename>')
def show_source(filename):
    with codecs.open(join(user_repo_path, 'build/html/_sources', filename), 'r', 'utf-8') as content_file:
        content = content_file.read()
    return Response(content, mimetype='text/txt')

@app.route('/<path:filename>')
def navigate(filename):
    print(filename)
    filename, file_extension = os.path.splitext(filename)
    if file_extension == "":
        file_extension = '.html'
    print(join(user_repo_path, 'build/html', filename + file_extension), 'r', 'utf-8')
    with codecs.open(join(user_repo_path, 'build/html', filename + file_extension), 'r', 'utf-8') as content_file:
        content = content_file.read()

    return render_template_string(content, content=content, standalone=True, render_sidebar=True)

@app.route('/images/<filename>')
def get_image(filename):
    return flask.send_from_directory(os.path.abspath('images'), filename)

@app.route('/login')
def login():
    return redirect(url_for('user.login'))

@app.route('/logout')
def logout():
    return redirect(url_for('user.logout'))
