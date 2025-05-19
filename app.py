import os
import logging
from flask import Flask, render_template, redirect, url_for, flash, current_app
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager, current_user
from markupsafe import Markup
from flask_mail import Mail, Message
from extensions import db
from models import User, JobPost, Student, Company

# Config logger
logging.basicConfig(level=logging.INFO)

def nl2br_filter(value):
    """Convertit les sauts de ligne en <br> HTML pour Jinja."""
    return Markup(value.replace("\n", "<br>\n"))

mail = Mail()  # Flask-Mail instance

def create_app():
    app = Flask(__name__)
    
    # Clé secrète session (à configurer dans l’environnement prod)
    app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

    # Proxy fix pour déploiement derrière un proxy
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # Filtres Jinja
    app.jinja_env.filters['nl2br'] = nl2br_filter

    # Base de données
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Configuration Flask-Mail sécurisée
    app.config.update(
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USE_SSL=False,
        MAIL_USERNAME=os.environ.get('MAIL_USERNAME'),
        MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD'),
        MAIL_DEFAULT_SENDER=os.environ.get('MAIL_USERNAME')
    )

    # Initialisation extensions
    db.init_app(app)
    mail.init_app(app)

    # Upload config
    upload_folder = os.path.join(app.root_path, "static", "uploads")
    app.config["UPLOAD_FOLDER"] = upload_folder
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max

    os.makedirs(os.path.join(upload_folder, "cvs"), exist_ok=True)
    os.makedirs(os.path.join(upload_folder, "profile_pics"), exist_ok=True)

    # Login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        db.create_all()

        # Création admin si inexistant
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(username='admin', email='admin@example.com')
            admin_user.set_password('Hacer123')
            admin_user.is_admin = True
            db.session.add(admin_user)
            db.session.commit()

        # ⚠️ En prod, ne pas forcer tous admin
        # for user in User.query.all():
        #     user.is_admin = True
        # db.session.commit()

    # Import blueprints
    from routes.auth import auth_bp
    from routes.student import student_bp
    from routes.company import company_bp
    from routes.jobs import jobs_bp
    from routes.messages import messages_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(admin_bp)

    # Routes principales
    @app.route('/')
    def home():
        return render_template('home.html')

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500

    @app.context_processor
    def inject_user_type():
        if current_user.is_authenticated:
            if Student.query.filter_by(user_id=current_user.id).first():
                return {"user_type": "student"}
            elif Company.query.filter_by(user_id=current_user.id).first():
                return {"user_type": "company"}
        return {"user_type": None}

    @app.route('/admin')
    def admin_dashboard():
        stats = {
            'total_users': User.query.count(),
            'total_students': Student.query.count(),
            'total_companies': Company.query.count(),
            'total_jobs': JobPost.query.count(),
            'recent_users': User.query.order_by(User.created_at.desc()).limit(5).all(),
            'recent_jobs': JobPost.query.order_by(JobPost.created_at.desc()).limit(5).all(),
            'application_status_counts': {
                'Pending': 5,
                'Accepted': 10,
                'Rejected': 3,
            },
            'recent_students': Student.query.order_by(Student.created_at.desc()).limit(5).all(),
            'recent_companies': Company.query.order_by(Company.created_at.desc()).limit(5).all(),
        }
        return render_template('admin/dashboard.html', stats=stats)

    @app.route('/job/<int:job_id>', methods=['GET'])
    def view_job_post(job_id):
        job = JobPost.query.get_or_404(job_id)
        return render_template('view_job_post.html', job=job)

    @app.route('/admin/job/delete/<int:job_id>', methods=['POST'])
    def delete_job(job_id):
        job = JobPost.query.get_or_404(job_id)
        db.session.delete(job)
        db.session.commit()
        flash("Job post deleted successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
    def delete_user(user_id):
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        flash("User deleted successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    @app.route('/student/<int:student_id>')
    def view_student_profile(student_id):
        student = Student.query.get_or_404(student_id)
        return render_template('student_profile.html', student=student)

    @app.route('/student/cv/<int:student_id>')
    def view_student_cv(student_id):
        student = Student.query.get_or_404(student_id)
        return redirect(url_for('static', filename=f'uploads/cvs/{student.cv_filename}'))

    return app

def send_email(to, subject, html):
    """Envoi d’un mail avec gestion simple des erreurs."""
    try:
        msg = Message(subject, recipients=[to], html=html, sender=current_app.config['MAIL_DEFAULT_SENDER'])
        mail.send(msg)
        logging.info(f"Email envoyé à {to} avec succès.")
    except Exception as e:
        logging.error(f"Erreur lors de l'envoi du mail à {to} : {e}")

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
