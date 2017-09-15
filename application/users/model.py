from flask_user import UserMixin

from application import db
from application.models import CRUDMixin

user_subscription = db.Table('user_subscription',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('named_tag', db.Integer, db.ForeignKey('named_tag.id'))
)

# Define the User data model. Make sure to add flask.ext.user UserMixin !!!
class User(CRUDMixin, UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    # User authentication information
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False, server_default='')
    reset_password_token = db.Column(db.String(100), nullable=False,
                                     server_default='')
    # User email information
    email = db.Column(db.String(75), nullable=False, unique=True)
    confirmed_at = db.Column(db.DateTime())
    # User information
    active = db.Column('is_active', db.Boolean(), nullable=False,
                       server_default='0')
    first_name = db.Column(db.String(100), nullable=False, server_default='')
    last_name = db.Column(db.String(100), nullable=False, server_default='')
    # User profile information
    string_property_01 = db.Column(db.String(80), nullable=True, unique=False)
    string_property_02 = db.Column(db.String(80), nullable=True, unique=False)
    string_property_03 = db.Column(db.String(80), nullable=True, unique=False)
    string_property_04 = db.Column(db.String(80), nullable=True, unique=False)
    string_property_05 = db.Column(db.String(80), nullable=True, unique=False)
    integer_property_01 = db.Column(db.Integer, nullable=True, unique=False)
    integer_property_02 = db.Column(db.Integer, nullable=True, unique=False)
    integer_property_03 = db.Column(db.Integer, nullable=True, unique=False)
    integer_property_04 = db.Column(db.Integer, nullable=True, unique=False)
    integer_property_05 = db.Column(db.Integer, nullable=True, unique=False)
    integer_property_06 = db.Column(db.Integer, nullable=True, unique=False)
    integer_property_07 = db.Column(db.Integer, nullable=True, unique=False)
    integer_property_08 = db.Column(db.Integer, nullable=True, unique=False)
    integer_property_09 = db.Column(db.Integer, nullable=True, unique=False)
    integer_property_10 = db.Column(db.Integer, nullable=True, unique=False)
    boolean_property_01 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_02 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_03 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_04 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_05 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_06 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_07 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_08 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_09 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_10 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_11 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_12 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_13 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_14 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_15 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_16 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_17 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_18 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_19 = db.Column(db.Boolean(), nullable=True, unique=False)
    boolean_property_20 = db.Column(db.Boolean(), nullable=True, unique=False)

    threads = db.relationship('Thread', backref='author', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    subscriptions = db.relationship(
        'Named_Tag', secondary=user_subscription,
        backref=db.backref('subscribed_users', lazy='dynamic'))

    @classmethod
    def get_by_name(cls, name):
        return cls.query.filter_by(username=name).first_or_404()


