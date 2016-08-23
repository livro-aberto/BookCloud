from sphinx_edit import app
import flask
import os
from flask import render_template, render_template_string, request, redirect
import codecs # deals with encoding better

from flask.ext.wtf import Form
#from flask.ext.codemirror.fields import CodeMirrorField
from wtforms.fields import SubmitField

# Change this password
app.config['SECRET_KEY'] = 'swell-secret-password'

class MyForm(Form):
    conf = {
        'lineNumbers': True,
        'autofocus': False
    }
    #source_code = CodeMirrorField(language='text/rst', config=conf)

user_repo_path = '/home/gutosurrex/gsync/Programming/leevro/repos/bla'

@app.route('/save', methods = ['GET', 'POST'])
def save():
    return "Saved"

@app.route('/edit/<filename>', methods = ['GET', 'POST'])
def edit(filename):
    #if request.method == 'POST':
    #    return redirect('/save')
    filename, file_extension = os.path.splitext(filename)
    with codecs.open(user_repo_path + '/build/html/'
                     + filename + '.html', 'r', 'utf-8') as content_file:
        doc = render_template_string(content_file.read(), standalone=False, render_sidebar=False)
    with codecs.open(user_repo_path + '/source/'
                     + filename + '.rst', 'r', 'utf-8') as content_file:
        rst = content_file.read()
    return render_template('edit.html', doc=doc, rst=rst)

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
    print("bla")
    filename, file_extension = os.path.splitext(filename)
    with codecs.open(user_repo_path + '/build/html/' + filename + '.html', 'r', 'utf-8') as content_file:
        content = content_file.read()

    return render_template_string(content, content=content, standalone=True,render_sidebar=True)

