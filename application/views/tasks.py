import re

from application import app, limiter, ext
from flask import jsonify

from application.views import internal_server_error

from pygtail import Pygtail

from celery.result import AsyncResult

#from werkzeug.utils import secure_filename

@limiter.exempt
@app.route('/tasks/<path:task_id>')
def tasks(task_id):
    task_id = re.sub('/', '', task_id)
    task = AsyncResult(task_id)

    if (task.state == 'PENDING'):
        return jsonify({ 'state': task.state })

    if (task.state == 'PROGRESS'):
        return jsonify({ 'state': task.state,
                         'status': task.info.get('status', '') })

    if (task.state == 'FAILURE'):
        internal_server_error(task.result)
        return jsonify({ 'state': task.state,
                         'result': task.result.message,
                         'traceback': task.traceback })

    if (task.state == 'SUCCESS'):
        return jsonify({ 'state': task.state })

    return jsonify({ 'state': task.state })

