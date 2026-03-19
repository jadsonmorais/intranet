from flask import Blueprint, redirect, url_for, render_template, flash, current_app
from flask_login import login_user, logout_user, login_required
from .extensions import oauth, db
from .models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login")
def login():
    return render_template("login.html")


@auth_bp.route("/login/google")
def login_google():
    redirect_uri = url_for("auth.authorize", _external=True)
    return oauth.google.authorize_redirect(
        redirect_uri,
        prompt="select_account"
    )


@auth_bp.route("/login/zoho")
def login_zoho():
    client = getattr(oauth, "zoho", None)
    if not client:
        flash("Login Zoho não configurado. Solicite ao TI.", "danger")
        return redirect(url_for("auth.login"))

    redirect_uri = url_for("auth.authorize_zoho", _external=True)
    return client.authorize_redirect(redirect_uri)


@auth_bp.route("/authorize")
def authorize():
    oauth.google.authorize_access_token()

    user_info = oauth.google.userinfo()
    email = (user_info.get("email") or "").strip().lower()
    name_from_google = (user_info.get("name") or "").strip()

    if not email:
        flash("Não foi possível obter o e-mail do Google.", "danger")
        return redirect(url_for("auth.login"))

    # ✅ Restringe por lista de domínios
    allowed_domains = current_app.config.get("ALLOWED_EMAIL_DOMAINS", [])
    if allowed_domains:
        email_domain = email.split("@")[-1].lower()
        if email_domain not in [d.lower() for d in allowed_domains]:
            flash("Acesso restrito a e-mails corporativos autorizados.", "danger")
            return redirect(url_for("auth.login"))

    # ✅ REGRA: usuário precisa existir e estar ativo (cadastrado pelo ADM)
    user = User.query.filter_by(email=email).first()

    if not user:
        flash("Seu usuário ainda não foi cadastrado pelo administrador. Solicite liberação ao TI.", "danger")
        return redirect(url_for("auth.login"))

    if not user.active:
        flash("Seu usuário está inativo. Solicite liberação ao TI.", "danger")
        return redirect(url_for("auth.login"))

    # Atualiza nome automaticamente apenas se estiver vazio (opcional)
    if (not user.name) and name_from_google:
        user.name = name_from_google
        db.session.commit()

    superadmin = current_app.config.get("SUPERADMIN_EMAIL", "").lower()
    if email == superadmin and not user.is_admin:
        user.is_admin = True
        db.session.commit()

    login_user(user)
    return redirect(url_for("main.area_bi"))


@auth_bp.route("/zoho/callback")
def authorize_zoho():
    client = getattr(oauth, "zoho", None)
    if not client:
        flash("Login Zoho não configurado. Solicite ao TI.", "danger")
        return redirect(url_for("auth.login"))

    token = client.authorize_access_token()

    user_info = {}
    try:
        user_info = client.parse_id_token(token)
    except Exception:
        try:
            user_info = client.userinfo()
        except Exception:
            user_info = {}

    email = (user_info.get("email") or "").strip().lower()
    name_from_zoho = (
        (user_info.get("name") or "")
        or (user_info.get("full_name") or "")
        or (user_info.get("display_name") or "")
    ).strip()

    if not email:
        flash("Não foi possível obter o e-mail do Zoho.", "danger")
        return redirect(url_for("auth.login"))

    allowed_domains = current_app.config.get("ALLOWED_EMAIL_DOMAINS", [])
    if allowed_domains:
        email_domain = email.split("@")[-1].lower()
        if email_domain not in [d.lower() for d in allowed_domains]:
            flash("Acesso restrito a e-mails corporativos autorizados.", "danger")
            return redirect(url_for("auth.login"))

    user = User.query.filter_by(email=email).first()

    if not user:
        flash("Seu usuário ainda não foi cadastrado pelo administrador. Solicite liberação ao TI.", "danger")
        return redirect(url_for("auth.login"))

    if not user.active:
        flash("Seu usuário está inativo. Solicite liberação ao TI.", "danger")
        return redirect(url_for("auth.login"))

    if (not user.name) and name_from_zoho:
        user.name = name_from_zoho
        db.session.commit()

    superadmin = current_app.config.get("SUPERADMIN_EMAIL", "").lower()
    if email == superadmin:
        if not user.is_admin:
            user.is_admin = True
            db.session.commit()

    login_user(user)
    return redirect(url_for("main.area_bi"))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
