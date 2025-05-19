import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')

    raw_database_url = os.environ.get('DATABASE_URL')
    if raw_database_url and raw_database_url.startswith("postgres://"):
        raw_database_url = raw_database_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = raw_database_url or 'sqlite:///site.db'

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    PREFERRED_URL_SCHEME = 'https'
