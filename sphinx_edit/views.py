from sphinx_edit import app
import flask
from flask import render_template
import codecs # deals with encoding better

#@app.route('/')
#def index():
#    return 'Hello World!'

@app.route('/comments/<filename>')
def get_comments(filename):
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
    return flask.send_from_directory( '/home/gutosurrex/gsync/Programming/grook/sphinx_edit/static/sphinx_static/',#app.config['UPLOAD_FOLDER'],
        filename
    )

@app.route('/', defaults={'filename': 'index.html'})
@app.route('/<path:filename>')
def documentation(filename):
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
        '/home/gutosurrex/rsync/Projetos/grook/bla/build/html/',#app.config['UPLOAD_FOLDER'],
        filename
    )
