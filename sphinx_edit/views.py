from sphinx_edit import app
import flask
import os
from flask import render_template, render_template_string, request, redirect
import codecs # deals with encoding better
import sphinx

from flask.ext.wtf import Form
#from flask.ext.codemirror.fields import CodeMirrorField
from wtforms.fields import SubmitField


def build(source_path, target_path, conf_path, flags):
    """
    Build documentation
    """
    # Replace this terrible implementation
    command = "sphinx-build -a -c " + conf_path + " " + source_path + " " + target_path + " "
    os.system(command)
    return True
    args = ['-c ' + conf_path]
    print(args)
    print([source_path, target_path])
    if len(flags):
        args = args + flags
    if sphinx.build_main(args + [source_path, target_path]):
        return False
    return True

# Change this password
app.config['SECRET_KEY'] = 'swell-secret-password'

class MyForm(Form):
    conf = {
        'lineNumbers': True,
        'autofocus': False
    }
    #source_code = CodeMirrorField(language='text/rst', config=conf)

user_repo_path = '/home/gutosurrex/gsync/Programming/leevro/repos/bla'
leevro_path = '/home/gutosurrex/gsync/Programming/leevro'

@app.route('/save/<filename>', methods = ['GET', 'POST'])
def save(filename):
    if request.method == 'POST':
        with codecs.open(user_repo_path + '/source/'
                  + filename + '.rst', 'w') as dest_file:
            dest_file.write(request.form['code'])
    build(user_repo_path + '/source', user_repo_path + '/build/html',
          leevro_path + '/conf/', '')
    return "Saved"

@app.route('/edit/<filename>', methods = ['GET', 'POST'])
def edit(filename):
    filename, file_extension = os.path.splitext(filename)
    if request.method == 'POST':
        with codecs.open(user_repo_path + '/source/'
                  + filename + '.rst', 'w') as dest_file:
            dest_file.write(request.form['code'])
    build(user_repo_path + '/source', user_repo_path + '/build/html',
          leevro_path + '/conf/', '')

    with codecs.open(user_repo_path + '/build/html/'
                     + filename + '.html', 'r', 'utf-8') as content_file:
        doc = render_template_string(content_file.read(), standalone=False, render_sidebar=False)
    with codecs.open(user_repo_path + '/source/'
                     + filename + '.rst', 'r', 'utf-8') as content_file:
        rst = content_file.read()
    return render_template('edit.html', doc=doc, rst=rst, filename=filename)

@app.route('/comment_summary/<filename>')
def comment_summary(filename):
    return "Comments from " + filename

@app.route('/_static/<filename>')
def resources(filename):
    return flask.send_from_directory( '/home/gutosurrex/gsync/Programming/leevro/sphinx_edit/static/sphinx_static/', filename)

#@app.route('/', defaults={'filename': 'index.html'})
@app.route('/<path:filename>')
#@app.route('/<path:filename>.html')
def navigate(filename):
    print(filename)
    filename, file_extension = os.path.splitext(filename)
    with codecs.open(user_repo_path + '/build/html/' + filename + '.html', 'r', 'utf-8') as content_file:
        content = content_file.read()

    return render_template_string(content, content=content, standalone=True,render_sidebar=True)

@app.route('/images/<filename>')
def get_image(filename):
    return flask.send_from_directory( '/home/gutosurrex/gsync/Programming/leevro/images', filename)
