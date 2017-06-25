from application import db
from sqlalchemy.orm import relationship

from application.models import CRUDMixin

class Project(CRUDMixin, db.Model):
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = relationship('User')
    branches = relationship('Branch', back_populates='project')

    def __init__(self, name, owner_id):
        self.name = name
        self.owner_id = owner_id
