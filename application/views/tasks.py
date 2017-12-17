from application import app
from flask import jsonify

from pygtail import Pygtail

from celery.result import AsyncResult

#from werkzeug.utils import secure_filename

@app.route('/tasks/<path:task_id>')
def tasks(task_id):
    res = AsyncResult(task_id)

    out = ""
    for line in Pygtail("log/BookCloud.log"):
        out = out + line

    return jsonify({ 'state': res.state, 'log': out })

