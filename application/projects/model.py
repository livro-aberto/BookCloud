import re
import json
import git
import os
from os.path import join, isfile, splitext
from shutil import copyfile

from flask_babel import gettext as _
from sqlalchemy.orm import relationship

from application import db, app
import application.branches
import application.threads
import application.users
from application.utils import load_file, write_file
from application.models import CRUDMixin

class FileExists(Exception):
    pass

class FileNotFound(Exception):
    pass

class FileNotEmpty(Exception):
    pass

class Project(CRUDMixin, db.Model):
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = relationship('User')
    branches = relationship('Branch', back_populates='project')
    threads = relationship('Thread', back_populates='project',
                           lazy='dynamic')

    # Has to be called only when one saves a file and the result stored
    # The labels of each file should be stored in database after save
    # keep in database?
    def get_labels(self):
        master_path = join('repos', self.name, 'master', 'source')
        label_list = []
        for f in os.listdir(master_path):
            if (isfile(join(master_path, f)) and f[0] != '.'):
                data = load_file(join(master_path, f))
                label_list.extend(re.findall(r'^\.\. _([0-9a-z\-]+):\s$',
                                             data, re.MULTILINE))
        return json.dumps(label_list)

    # Has to be called only when one saves a file and the result stored
    # The labels of each file should be stored in database after save
    def get_label_file_dict(self):
        master_path = join('repos', self.name, 'master', 'source')
        label_dict = {}
        for f in os.listdir(master_path):
            if (isfile(join(master_path, f)) and f[0] != '.'):
                stem, file_extension = os.path.splitext(f)
                data = load_file(join(master_path, f))
                more_data = {x: stem for x in re.findall(
                    r'^\.\. _([0-9a-z\-]+):\s$', data, re.MULTILINE)}
                label_dict.update(more_data)
        return label_dict

    def get_master(self):
        return (application.branches.Branch.query
                .filter_by(project_id=self.id, name='master').one())

    def get_branch(self, name):
        return (application.branches.Branch.query
                .filter_by(project_id=self.id, name=name).one())

    # will be deprecated (files should be in database)
    def get_files(self):
        path = self.get_master().get_source_path()
        return [f for f in os.listdir(path)
                if isfile(join(path, f)) and f[0] != '.']

    def get_folder(self):
        return join('repos', self.name)

    # Wrap in queued job
    # Should be sent to branch
    def new_file(self, filename):
        file_extension = '.rst'
        file_path = join(self.get_master().get_source_path(),
                         filename + file_extension)
        if os.path.isfile(file_path):
            raise FileExists
        else:
            stars = '*' * len(filename) + '\n'
            write_file(file_path, stars + filename + '\n' + stars)
            repo = self.get_master().get_repo()
            repo.index.add([filename + file_extension])
            self.get_master().build()
        app.logger.info('New file "{}" created'.format(filename))

    # Wrap in queued job
    # Should be sent to branch
    def rename_file(self, old_filename, new_filename):
        file_extension = '.rst'
        if not os.path.isfile(join(self.get_master().get_source_path(),
                                   old_filename + file_extension)):
            raise FileNotFound
        if os.path.isfile(join(self.get_master().get_source_path(),
                               new_filename + file_extension)):
            raise FileExists
        git_api = self.get_master().get_git()
        git_api.mv(old_filename + file_extension,
                   new_filename + file_extension)
        self.get_master().build()
        app.logger.info('File "{}" renamed to "{}"'.format(
            old_filename, new_filename))

    # Wrap in queued job
    # Should be sent to branch
    def delete_file(self, filename):
        file_extension = '.rst'
        if not os.path.isfile(join(self.get_master().get_source_path(),
                                   filename + file_extension)):
            raise FileNotFound
        if not os.stat(join(self.get_master().get_source_path(),
                            filename + file_extension)).st_size == 0:
            raise FileNotEmpty
        git_api = self.get_master().get_git()
        git_api.rm('-f', filename + file_extension)
        self.get_master().build()
        app.logger.info('File "{}" deleted'.format(filename))

    # The labels in a file should be stored in database after save
    def get_threads_by_tag(self, filename):
        try:
            data = load_file(join('repos', self.name, 'master',
                                  'source', filename + '.rst'))
        except:
            return []
        label_list = re.findall(r'^\.\. _([0-9a-z\-]+):\s$', data,
                                re.MULTILINE)
        File_Tag = application.threads.File_Tag
        Thread = application.threads.Thread
        threads_by_tag = (db.session.query(File_Tag.filename, Thread.title)
                          .filter(File_Tag.thread_id==Thread.id)
                          .filter(File_Tag.filename.in_(label_list)).all())
        return [{'name': l,
                 'titles': [x[1] for x in threads_by_tag if x[0]==l]}
                for l in label_list]

    def __init__(self, name, user_id):
        app.logger.info('Creating project "{}"...'.format(name))
        self.name = name
        user = get_by_id(user_id)
        self.owner_id = user.id
        # create the master branch
        new_branch = application.branches.Branch('master', self, None, user)
        db.session.add(new_branch)
        db.session.commit()
        # updating branch's self reference
        new_branch.origin_id = new_branch.id
        db.session.commit()
        # create folder for resources
        app.logger.info('Creating "{}" resource folders'.format(name))
        os.makedirs(join('repos', name, '_resources'))
        os.makedirs(join('repos', name, '_resources/original'))
        os.makedirs(join('repos', name, '_resources/low_resolution'))
        os.makedirs(join('repos', name, '_resources/thumbnail'))
        # create the repository in the filesystem
        app.logger.info('Creating "{}" repository'.format(name))
        repo_path = join('repos', name, 'master/source')
        os.makedirs(repo_path)
        os.symlink(os.path.abspath(join('repos', name, '_resources',
                                        'low_resolution')),
                   os.path.abspath(join('repos', name,
                                        'master/source/_resources/')))
        git.Repo.init(repo_path)
        repo = git.Repo(repo_path)
        application.branches.config_repo(repo, user.username, user.email)
        copyfile('empty_repo/source/index.rst', join(repo_path, 'index.rst'))
        copyfile('empty_repo/.gitignore', join(repo_path, '.gitignore'))
        repo.index.add(['index.rst', '.gitignore'])
        author = git.Actor(user.username, user.email)
        repo.index.commit(_('Initial commit'), author=author)
        new_branch.build(timeout=30)
        db.session.add(self)
        db.session.commit()
        app.logger.info('Project "{}" created'.format(name))

