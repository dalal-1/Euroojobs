from extensions import db  # Absolute import instead of relative import
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class Base(db.Model):
    __abstract__ = True  # This ensures no table will be created for Base directly
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class User(UserMixin, Base):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    
    # Champs ajoutés pour confirmation email et reset mot de passe
    is_confirmed = db.Column(db.Boolean, default=False)
    confirmed_on = db.Column(db.DateTime, nullable=True)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiration = db.Column(db.DateTime, nullable=True)

    # Relations
    student = db.relationship('Student', backref='user', uselist=False, cascade="all, delete-orphan")
    company = db.relationship('Company', backref='user', uselist=False, cascade="all, delete-orphan")
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    messages_sent = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic', cascade="all, delete-orphan")
    messages_received = db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient', lazy='dynamic', cascade="all, delete-orphan")
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Student(Base):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    profile_picture = db.Column(db.String(256))
    cv_file = db.Column(db.String(256))
    bio = db.Column(db.Text)
    education = db.Column(db.Text)
    phone = db.Column(db.String(20))
    website = db.Column(db.String(120))
    
    skills = db.relationship('Skill', backref='student', lazy='dynamic', cascade="all, delete-orphan")
    applications = db.relationship('Application', backref='student', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Student {self.first_name} {self.last_name}>'

class Skill(Base):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    level = db.Column(db.Integer, default=1)  # Skill level from 1-5
    
    def __repr__(self):
        return f'<Skill {self.name}>'

class Company(Base):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    logo = db.Column(db.String(256))
    description = db.Column(db.Text)
    industry = db.Column(db.String(64))
    website = db.Column(db.String(120))
    location = db.Column(db.String(128))
    size = db.Column(db.String(32))  # e.g., "1-10", "11-50", etc.
    founded_year = db.Column(db.Integer)
    
    job_posts = db.relationship('JobPost', backref='company', lazy='dynamic', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Company {self.name}>'

class JobPost(Base):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text)
    location = db.Column(db.String(128))
    job_type = db.Column(db.String(32))  # Full-time, Part-time, Internship, etc.
    salary_min = db.Column(db.Float)
    salary_max = db.Column(db.Float)
    is_active = db.Column(db.Boolean, default=True)
    deadline = db.Column(db.DateTime)
    
    applications = db.relationship('Application', backref='job_post', lazy='dynamic', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<JobPost {self.title}>'

class Application(Base):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    job_post_id = db.Column(db.Integer, db.ForeignKey('job_post.id'), nullable=False)
    cover_letter = db.Column(db.Text)
    status = db.Column(db.String(32), default='pending')  # pending, reviewing, rejected, accepted
    
    def __repr__(self):
        return f'<Application {self.id}>'

class Message(Base):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<Message {self.id}>'

class Notification(Base):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(256))
    read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Notification {self.id}>'

class Conversation(Base):
    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    user1 = db.relationship('User', foreign_keys=[user1_id])
    user2 = db.relationship('User', foreign_keys=[user2_id])
    
    def __repr__(self):
        return f'<Conversation {self.id}>'

# Fonction utilitaire pour suppression sécurisée par admin
def secure_delete(model, obj_id, admin_user):
    if not admin_user.is_admin:
        raise PermissionError("You must be an admin to delete this object.")
    obj = model.query.get(obj_id)
    if obj:
        db.session.delete(obj)
        db.session.commit()
    else:
        raise ValueError(f"Object with id {obj_id} not found.")
