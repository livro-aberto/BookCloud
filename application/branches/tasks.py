import os

from os.path import join

from application import app, ext, db
from application.projects import Project

celery = ext.celery

@celery.task(bind=True)
def build_branch(self, branch_id):
    branch = Branch.query.filter_by(id=branch_id).one()
    app.logger.info('Building branch "{}" of "{}"'.format(
        branch.name, branch.project.name))
    # Replace this terrible implementation
    config_path = 'conf'
    branch_path = os.path.abspath(join(os.getcwd(), 'repos',
                                       branch.project.name, branch.name))
    log_file_name = join(app.config['SPHINX_LOGGING_FOLDER'],
                         'sphinx' + str(uuid.uuid4())) + '.log'
    args = ['-v', '-v',
            '-w', log_file_name,
            '-c', os.path.abspath('conf'),
            join(branch_path, 'source'), join(branch_path, 'build/html')]
    result = sphinx.build_main(args)
    if (result == 0):
        return True, log_file_name
    else:
        return False
