from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from extensions import db, mail
from models import User, Student, Company
from forms import LoginForm, RegistrationForm, ResetPasswordRequestForm, ResetPasswordForm
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask_mail import Message
from bs4 import BeautifulSoup

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

APP_NAME = "EuroJobs"  # Nom de l'application centralisé

def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='email-confirm-salt')

def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='email-confirm-salt', max_age=expiration)
    except (SignatureExpired, BadSignature):
        return False
    return email

def send_email(to, subject, html_template):
    text_body = BeautifulSoup(html_template, "html.parser").get_text()
    msg = Message(subject=subject,
                  recipients=[to],
                  sender=current_app.config['MAIL_DEFAULT_SENDER'])
    msg.body = text_body
    msg.html = html_template
    mail.send(msg)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Redirection selon rôle
        if getattr(current_user, 'is_admin', False):
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('home'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password', 'danger')
            return redirect(url_for('auth.login'))
        if not user.is_active:
            flash('Please confirm your email address before logging in.', 'warning')
            return redirect(url_for('auth.login'))

        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        # Sécurité : s'assurer que next_page est relatif (pas une URL externe)
        if not next_page or urlparse(next_page).netloc != '':
            if getattr(current_user, 'is_admin', False):
                next_page = url_for('admin.dashboard')
            elif Student.query.filter_by(user_id=user.id).first():
                next_page = url_for('student.profile')
            elif Company.query.filter_by(user_id=user.id).first():
                next_page = url_for('company.profile')
            else:
                next_page = url_for('home')
        return redirect(next_page)

    return render_template('auth/login.html', title='Sign In', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, is_active=False)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()  # flush pour avoir l'id avant commit

        if form.account_type.data == 'student':
            student = Student(user_id=user.id)
            db.session.add(student)
        else:
            company = Company(user_id=user.id, name=form.username.data)
            db.session.add(company)

        db.session.commit()

        token = generate_confirmation_token(user.email)
        confirm_url = url_for('auth.confirm_email', token=token, _external=True)
        html = render_template('auth/activate.html', confirm_url=confirm_url, user=user)
        subject = f"{APP_NAME} – Please confirm your email, {user.username}"
        send_email(user.email, subject, html)

        flash('A confirmation email has been sent. Please confirm to activate your account.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', title='Register', form=form)

@auth_bp.route('/confirm/<token>')
def confirm_email(token):
    email = confirm_token(token)
    if not email:
        flash('The confirmation link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=email).first_or_404()
    if user.is_active:
        flash('Account already confirmed. Please login.', 'success')
    else:
        user.is_active = True
        db.session.commit()
        flash('You have confirmed your account. Thanks!', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@auth_bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = generate_confirmation_token(user.email)
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            html = render_template('auth/reset_password_email.html', reset_url=reset_url, user=user)
            subject = f"{APP_NAME} – Password Reset Request for {user.username}"
            send_email(user.email, subject, html)
            flash('Check your email for instructions to reset your password.', 'info')
        else:
            flash('Email address not found.', 'warning')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html', form=form)

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = confirm_token(token)
    if not email:
        flash('The reset link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.reset_password_request'))
    user = User.query.filter_by(email=email).first_or_404()
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been updated.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)
