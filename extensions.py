from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail

db = SQLAlchemy()
mail = Mail()

def init_app(app):
    db.init_app(app)
    mail.init_app(app)
