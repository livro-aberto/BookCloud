import re
import json
import git
import os
from os.path import join, isfile, splitext
from shutil import copyfile

from flask_babel import gettext as _
from sqlalchemy.orm import relationship

from application import db
import application.branches
import application.threads
import application.users
from application.tools import load_file, write_file
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

    def get_labels(self):
        master_path = join('repos', self.name, 'master', 'source')
        label_list = []
        for f in os.listdir(master_path):
            if (isfile(join(master_path, f)) and f[0] != '.'):
                data = load_file(join(master_path, f))
                label_list.extend(
                    [splitext(f)[0] + '#' + l for l in
                     re.findall(r'^\.\. _([a-z\-]+):\s$', data, re.MULTILINE)])
        return json.dumps(label_list)

    #def get_repo_path(self):
    #    return join('repos', self.name)

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
            application.branches.build(self.name, 'master')

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
        application.branches.build(self.name, 'master')

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
        application.branches.build(self.name, 'master')

    def get_threads_by_tag(self, filename):
        label_list = []
        data = load_file(join('repos', self.name, 'master',
                              'source', filename + '.rst'))
        label_list.extend([l for l in re.findall(r'^\.\. _([a-z\-]+):\s$',
                                                 data, re.MULTILINE)])
        File_Tag = application.threads.File_Tag
        Thread = application.threads.Thread
        threads_by_tag = (db.session.query(File_Tag.filename, Thread.title)
                          .filter(File_Tag.filename.like(filename + '#' + '%'))
                          .filter(File_Tag.thread_id==Thread.id).all())
        return [
            {'name': name,
             'fullname': filename + '%23' + name,
             'titles': [x[1] for x in threads_by_tag
                        if x[0].split('#')[1] == name]} for name in label_list]



    def __init__(self, name, user):
        self.name = name
        self.owner_id = user.id
        # create the master branch
        new_branch = application.branches.Branch('master', self, None, user)
        db.session.add(new_branch)
        db.session.commit()
        # updating branch's self reference
        new_branch.origin_id = new_branch.id
        db.session.commit()
        # create the repository in the filesystem
        repo_path = join('repos', name, 'master/source')
        os.makedirs(repo_path)
        git.Repo.init(repo_path)
        repo = git.Repo(repo_path)
        application.branches.config_repo(repo, user.username, user.email)
        copyfile('empty_repo/source/index.rst', join(repo_path, 'index.rst'))
        copyfile('empty_repo/.gitignore', join(repo_path, '.gitignore'))
        repo.index.add(['index.rst', '.gitignore'])
        author = git.Actor(user.username, user.email)
        repo.index.commit(_('Initial commit'), author=author)
        application.branches.build(name, 'master')
