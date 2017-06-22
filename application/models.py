from flask import abort
from flask_user import UserMixin

from application import db

from sqlalchemy.orm import relationship

class CRUDMixin(object):
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)

    @classmethod
    def get_by_id(cls, id):
        if any(
            (isinstance(id, basestring) and id.isdigit(),
             isinstance(id, (int, float))),
        ):
            response = cls.query.get(int(id))
            if not response:
                abort(404)
            return response
        abort(404)

    @classmethod
    def get_by_name(cls, name):
        return cls.query.filter_by(name=name).first_or_404()

    @classmethod
    def create(cls, **kwargs):
        instance = cls(**kwargs)
        return instance.save()

    def update(self, commit=True, **kwargs):
        for attr, value in kwargs.iteritems():
            setattr(self, attr, value)
        return commit and self.save() or self

    def save(self, commit=True):
        db.session.add(self)
        if commit:
            db.session.commit()
        return self

    def delete(self, commit=True):
        db.session.delete(self)
        return commit and db.session.commit()

class Project(db.Model):
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = relationship('User')
    branches = relationship('Branch', back_populates='project')

    def __init__(self, name, owner_id):
        self.name = name
        self.owner_id = owner_id

class Branch(db.Model):
    __tablename__ = 'branch'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    origin_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    expires = db.Column('expires', db.Boolean(), nullable=False)
    expiration =  db.Column(db.DateTime)

    owner = relationship('User')
    origin = relationship('Branch', remote_side=id)
    collaborators = relationship('Branch')
    project = relationship('Project', back_populates='branches')

    def __init__(self, name, project_id, origin_id, owner_id):
        self.name = name
        self.owner_id = owner_id
        self.origin_id = origin_id
        self.project_id = project_id
        self.expires = True

