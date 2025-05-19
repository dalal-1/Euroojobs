import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')

    # On s'assure que Render fournit la variable DATABASE_URL
    raw_database_url = os.environ.get('DATABASE_URL')
    if raw_database_url and raw_database_url.startswith("postgres://"):
        # Render donne parfois "postgres://" au lieu de "postgresql://", SQLAlchemy exige le bon format
        raw_database_url = raw_database_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = raw_database_url or 'sqlite:///site.db'

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Ne PAS mettre SERVER_NAME avec une URL complète — Flask l’utilise pour autre chose
    # Supprimé pour éviter les erreurs

    # Utilisation du schéma HTTPS pour les URL générées (optionnel)
    PREFERRED_URL_SCHEME = 'https'
