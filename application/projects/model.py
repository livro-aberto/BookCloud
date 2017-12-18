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

    def __init__(self, name, user):
        self.name = name
        self.owner_id = user.id
