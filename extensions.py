from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail

db = SQLAlchemy()
mail = Mail()

def init_app(app):
    # Initialise les extensions avec l'app Flask
    db.init_app(app)
    mail.init_app(app)

    # Crée les tables dans la base de données si elles n'existent pas déjà
    with app.app_context():
        db.create_all()
