from sphinx_edit import app
import flask
from flask import render_template, request, redirect
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

user_repo_path = '/home/gutosurrex/rsync/Projetos/grook/bla'

@app.route('/save', methods = ['GET', 'POST'])
def save():
    return "Saved"

@app.route('/edit/<filename>', methods = ['GET', 'POST'])
def edit(filename):
    #if request.method == 'POST':
    #    return redirect('/save')
    with codecs.open(user_repo_path + '/build/bare/'
                     + filename + '.html', 'r', 'utf-8') as content_file:
        doc = content_file.read()
    with codecs.open(user_repo_path + '/source/'
                     + filename + '.rst', 'r', 'utf-8') as content_file:
        rst = content_file.read()
    return render_template('edit.html', doc=doc, rst=rst)

@app.route('/comment_summary/<filename>')
def comment_summary(filename):
    return "Comments from " + filename

@app.route('/_static/<filename>')
def resources(filename):
    # to return a sub html
    # with codecs.open('/tmp/bla/build/html/index.html', 'r', 'utf-8') as content_file:
    #     content = content_file.read()
    #
    # content.encode('utf-8')
    # print(content)
    # return render_template('view.html', content=content)

    #return render_template('view.html', content="abc")
    #return '<iframe srcdoc="' + content + '</iframe>'
    #return '<frame src="/tmp/bla/build/html/index.html"></iframe>'

    # Replace this by
    return flask.send_from_directory( '/home/gutosurrex/gsync/Programming/leevro/sphinx_edit/static/sphinx_static/',#app.config['UPLOAD_FOLDER'],
        filename
    )

@app.route('/', defaults={'filename': 'index.html'})
@app.route('/<path:filename>')
def navigate(filename):
    # to return a sub html
    # with codecs.open('/tmp/bla/build/html/index.html', 'r', 'utf-8') as content_file:
    #     content = content_file.read()
    #
    # content.encode('utf-8')
    # print(content)
    # return render_template('view.html', content=content)

    #return render_template('view.html', content="abc")
    #return '<iframe srcdoc="' + content + '</iframe>'
    #return '<frame src="/tmp/bla/build/html/index.html"></iframe>'
    return flask.send_from_directory(
        user_repo_path + '/build/html/',#app.config['UPLOAD_FOLDER'],
        filename
    )
