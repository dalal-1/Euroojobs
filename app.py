import os
import logging
from flask import Flask, render_template, redirect, url_for, flash, current_app, abort
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager, current_user, login_required
from markupsafe import Markup
from flask_mail import Mail, Message
from extensions import db
from models import User, JobPost, Student, Company

# Configuration des logs
logging.basicConfig(level=logging.DEBUG)

# Filtre Jinja : sauts de ligne vers <br>
def nl2br_filter(value):
    return Markup(value.replace("\n", "<br>\n"))

mail = Mail()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    app.jinja_env.filters['nl2br'] = nl2br_filter

    # Config base de données
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_recycle": 300, "pool_pre_ping": True}
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Config mail
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'dalaloumayma@gmail.com')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'cymiqbdutvdwiwrv')
    app.config['MAIL_DEFAULT_SENDER'] = (app.config['MAIL_USERNAME'], app.config['MAIL_USERNAME'])

    db.init_app(app)
    mail.init_app(app)

    # Fichiers upload
    upload_folder = os.path.join(app.root_path, "static", "uploads")
    app.config["UPLOAD_FOLDER"] = upload_folder
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB
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

    # Init DB + admin user unique
    with app.app_context():
        db.create_all()
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(username='admin', email='admin@example.com')
            admin_user.set_password('Hacer123')
            admin_user.is_admin = True
            db.session.add(admin_user)
            db.session.commit()

    # Blueprints
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
    @login_required
    def admin_dashboard():
        if not current_user.is_admin:
            abort(403)
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
    @login_required
    def delete_job(job_id):
        if not current_user.is_admin:
            abort(403)
        job = JobPost.query.get_or_404(job_id)
        db.session.delete(job)
        db.session.commit()
        flash("Job post deleted successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
    @login_required
    def delete_user(user_id):
        if not current_user.is_admin:
            abort(403)
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

# Envoi d’e-mail : version améliorée pour éviter les spams
def send_email(to, subject, html):
    msg = Message(subject,
                  recipients=[to],
                  html=html,
                  sender=current_app.config['MAIL_DEFAULT_SENDER'],
                  reply_to=current_app.config['MAIL_USERNAME'])
    msg.body = "This is an HTML email. Please view in an HTML-compatible client."
    mail.send(msg)

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
