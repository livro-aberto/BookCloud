from application import db
from sqlalchemy.orm import relationship
import application.users

from application.tools import window, rst2html

# Classes for threads and comments

class Thread(db.Model):
    # One thread holds several comments and is associated to a project
    __tablename__ = 'thread'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Unicode(80), nullable=False, unique=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = relationship('User')
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    project = relationship('Project')
    flag = db.Column(db.String(10), nullable=False)
    posted_at = db.Column(db.DateTime(), nullable=False)

    def __init__(self, title, owner_id, project_id, flag, posted_at):
        self.title = title
        self.owner_id = owner_id
        self.project_id = project_id
        print(posted_at)
        self.posted_at = posted_at
        self.flag = flag

    def get_number_of_comments(self):
        return Comment.query.filter_by(thread_id=self.id).count()

    def get_comments(self, number):
        return Comment.query.filter_by(thread_id=self.id).order_by(Comment.lineage).limit(number)

    def get_user_tags(self):
        return User_Tag.query.filter_by(thread_id=self.id)

    def get_file_tags(self):
        return File_Tag.query.filter_by(thread_id=self.id)

    def get_custom_tags(self):
        return Custom_Tag.query.filter_by(thread_id=self.id)

    def get_free_tags(self):
        return Free_Tag.query.filter_by(thread_id=self.id)

class Comment(db.Model):
    # Comments have a father thread and a lineage inside that thread.
    # The lineage encodes where in the thread tree that command appears
    __tablename__ = 'comment'
    id = db.Column(db.Integer, primary_key=True)
    lineage = db.Column(db.String(200))
    thread_id = db.Column(db.Integer, db.ForeignKey('thread.id'))
    thread = relationship('Thread')
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = relationship('User')
    content = db.Column(db.Unicode(2000), nullable=False, unique=False)
    posted_at = db.Column(db.DateTime(), nullable=False)

    def __init__(self, lineage, thread_id, owner_id, content, posted_at):
        self.lineage = lineage
        self.thread_id = thread_id
        self.owner_id = owner_id
        self.content = content
        self.posted_at = posted_at

    def get_indent(self):
        return 6 * len(self.lineage)

    def get_likes(self):
        return Likes.query.filter_by(comment_id=self.id).count()

    def has_replies(self):
        decendants = self.lineage + '%'
        decend_comments = (Comment.query
                           .filter(Comment.thread_id==self.thread_id)
                           .filter(Comment.lineage.like(decendants)).all())
        return len(decend_comments) > 1

class Likes(db.Model):
    # Associates a like to a comment
    __tablename__ = 'likes'
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'))
    comment = relationship('Comment')
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = relationship('User')

    def __init__(self, comment_id, owner_id):
        self.comment_id = comment_id
        self.owner_id = owner_id

class User_Tag(db.Model):
    # Associates a user to a thread
    __tablename__ = 'user_tag'
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('thread.id'))
    thread = relationship('Thread')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = relationship('User')

    def __init__(self, thread_id, user_id):
        self.thread_id = thread_id
        self.user_id = user_id

class File_Tag(db.Model):
    # Associates a file to a thread
    __tablename__ = 'file_tag'
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('thread.id'))
    thread = relationship('Thread')
    filename = db.Column(db.String(50), nullable=False, unique=False)

    def __init__(self, thread_id, filename):
        self.thread_id = thread_id
        self.filename = filename

class Named_Tag(db.Model):
    # Tags that are created by moderators
    __tablename__ = 'named_tag'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False, unique=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    project = relationship('Project')

    def __init__(self, name, project_id):
        self.name = name
        self.project_id = project_id

class Custom_Tag(db.Model):
    # Associates a named_tag to a thread
    __tablename__ = 'custom_tag'
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('thread.id'))
    thread = relationship('Thread')
    named_tag_id = db.Column(db.Integer, db.ForeignKey('named_tag.id'))
    named_tag = relationship('Named_Tag')

    def __init__(self, thread_id, named_tag_id):
        self.thread_id = thread_id
        self.named_tag_id = named_tag_id

class Free_Tag(db.Model):
    # Associates a free-named tag to a thread
    __tablename__ = 'free_tag'
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('thread.id'))
    thread = relationship('Thread')
    name = db.Column(db.String(20), nullable=False)

    def __init__(self, thread_id, name):
        self.thread_id = thread_id
        self.name = name

