import os
import sphinx

from os.path import join

import model

from application import app, ext, db

celery = ext.celery

@celery.task(bind=True)
def build_branch(self, branch_id):
    branch = model.Branch.query.filter_by(id=branch_id).one()
    print("AAA")
    message = 'Building branch "{}" of "{}"'.format(branch.name,
                                                    branch.project.name)
    app.logger.info(message)
    self.update_state(state='PROGRESS', meta={'status': message})
    print(self.AsyncResult(self.request.id).state)
    branch_path = os.path.abspath(join(os.getcwd(), 'repos',
                                       branch.project.name, branch.name))
    log_file_name = join(app.config['SPHINX_LOGGING_FOLDER'],
                         'sphinx-' + self.request.id + '.log')
    args = ['-v', '-v',
            '-w', log_file_name,
            '-c', os.path.abspath('conf'),
            join(branch_path, 'source'), join(branch_path, 'build/html')]
    result = sphinx.build_main(args)
    print("CCC")
    if (result == 0):
        return True, log_file_name
    else:
        return False

@celery.task(bind=True)
def build_branch_latex(self, branch_id):
    branch = model.Branch.query.filter_by(id=branch_id).one()

    message = ('Building latex for branch "{}" of "{}"'
               .format(branch.name, branch.project.name))
    app.logger.info(message)
    self.update_state(state='PROGRESS', meta={'status': message})

    # Replace this terrible implementation
    config_path = 'conf'
    source_path = join('repos', branch.project.name, branch.name, 'source')
    build_path = join('repos', branch.project.name, branch.name, 'build/latex')
    command = ('sphinx-build -a -b latex -c ' + config_path + ' '
               + source_path + ' ' + build_path)
    os.system(command)
    return True

@celery.task(bind=True)
def compile_pdf(self, branch_id):
    branch = model.Branch.query.filter_by(id=branch_id).one()

    message = ('Building latex for branch "{}" of "{}"'
               .format(branch.name, branch.project.name))
    app.logger.info(message)
    self.update_state(state='PROGRESS', meta={'status': message})

    build_path = os.path.abspath(join('repos', branch.project.name, branch.name,
                                      'build/latex'))

    command = ('(cd ' + build_path
               + '; pdflatex -interaction nonstopmode linux.tex'
               + '> /tmp/222 || true)')
    os.system(command)


    # try:
    #     os.makedirs('/etc/seelekj')
    # except:
    #     self.update_state(state='FAILURE', meta={'status': 'Could not do it'})

