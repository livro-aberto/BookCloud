from sphinx_edit import app
from flask.ext.codemirror import CodeMirror

# mandatory
CODEMIRROR_LANGUAGES = ['rst']


app.config.from_object(__name__)
codemirror = CodeMirror(app)
app.run(debug=True)
