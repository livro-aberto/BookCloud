from application import db
from sqlalchemy.orm import relationship

from application.models import CRUDMixin

# Classes for threads and comments

user_tags = db.Table('user_tag',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('thread_id', db.Integer, db.ForeignKey('thread.id'))
)

likes = db.Table('likes',
    db.Column('comment_id', db.Integer, db.ForeignKey('comment.id')),
    db.Column('owner_id', db.Integer, db.ForeignKey('user.id'))
)

custom_tags = db.Table('custom_tag',
    db.Column('thread_id', db.Integer, db.ForeignKey('thread.id')),
    db.Column('named_tag_id', db.Integer, db.ForeignKey('named_tag.id'))
)

class Thread(CRUDMixin, db.Model):
    # One thread holds several comments
    # and is associated to a project
    __tablename__ = 'thread'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Unicode(80), nullable=False, unique=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = relationship('User')
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    project = relationship('Project')
    flag = db.Column(db.String(10), nullable=False)
    posted_at = db.Column(db.DateTime(), nullable=False)

    comments = db.relationship('Comment', back_populates='thread', lazy='dynamic')
    user_tags = db.relationship('User', secondary=user_tags,
                                backref=db.backref('tagged_threads', lazy='dynamic'))
    custom_tags = db.relationship('Named_Tag', secondary=custom_tags,
                                  backref=db.backref('threads', lazy='dynamic'))
    file_tags = db.relationship('File_Tag', back_populates='thread', lazy='dynamic')
    free_tags = db.relationship('Free_Tag', back_populates='thread', lazy='dynamic')

    def __init__(self, title, owner_id, project_id, flag, posted_at):
        self.title = title
        self.owner_id = owner_id
        self.project_id = project_id
        print(posted_at)
        self.posted_at = posted_at
        self.flag = flag

    def get_comments(self, number):
        return Comment.query.filter_by(thread_id=self.id).order_by(Comment.lineage).limit(number)

class Comment(CRUDMixin, db.Model):
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

    thread = db.relationship('Thread', back_populates='comments')
    likes = db.relationship('User', secondary=likes, lazy='dynamic',
                            backref=db.backref('liked_commends', lazy='dynamic'))

    def __init__(self, lineage, thread_id, owner_id, content, posted_at):
        self.lineage = lineage
        self.thread_id = thread_id
        self.owner_id = owner_id
        self.content = content
        self.posted_at = posted_at

    def get_indent(self):
        return 6 * len(self.lineage)

    def has_replies(self):
        decendants = self.lineage + '%'
        decend_comments = (Comment.query
                           .filter(Comment.thread_id==self.thread_id)
                           .filter(Comment.lineage.like(decendants)).all())
        return len(decend_comments) > 1

class File_Tag(CRUDMixin, db.Model):
    # Associates a file to a thread
    __tablename__ = 'file_tag'
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('thread.id'))
    thread = relationship('Thread')
    filename = db.Column(db.String(50), nullable=False, unique=False)

    def __init__(self, thread_id, filename):
        self.thread_id = thread_id
        self.filename = filename

class Named_Tag(CRUDMixin, db.Model):
    # Tags that are created by moderators
    __tablename__ = 'named_tag'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False, unique=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    project = relationship('Project')

    def __init__(self, name, project_id):
        self.name = name
        self.project_id = project_id

class Free_Tag(CRUDMixin, db.Model):
    # Associates a free-named tag to a thread
    __tablename__ = 'free_tag'
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('thread.id'))
    thread = relationship('Thread')
    name = db.Column(db.String(20), nullable=False)

    def __init__(self, thread_id, name):
        self.thread_id = thread_id
        self.name = name

