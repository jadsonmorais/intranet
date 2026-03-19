from flask import Blueprint, render_template, redirect, url_for, abort
from flask_login import login_required, current_user

from .extensions import db
from .models import Dashboard, UserDashboard

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.area_bi"))
    return redirect(url_for("auth.login"))


@main_bp.route("/bi/")
@login_required
def area_bi():
    setores = agrupa_dashboards_por_usuario(current_user.id)
    return render_template("area_bi.html", setores=setores)


@main_bp.route("/bi/<sector>/<slug>/")
@login_required
def dashboard_embed(sector, slug):
    dash = Dashboard.query.filter_by(
        sector=sector.upper(),
        slug=slug
    ).first()

    if not dash:
        abort(404)

    allowed = UserDashboard.query.filter_by(user_id=current_user.id, dashboard_id=dash.id).first()
    if not allowed and not getattr(current_user, "is_admin", False):
        abort(403)

    return render_template("dashboard_embed.html", dashboard=dash)


def agrupa_dashboards_por_usuario(user_id: int):
    """
    Retorna somente os dashboards liberados para o usuário (via user_dashboard).
    Se o usuário for admin, retorna todos.
    """
    # Admin vê tudo
    if getattr(current_user, "is_admin", False):
        dashboards = Dashboard.query.order_by(Dashboard.sector, Dashboard.name).all()
    else:
        dashboards = (
            db.session.query(Dashboard)
            .join(UserDashboard, UserDashboard.dashboard_id == Dashboard.id)
            .filter(UserDashboard.user_id == user_id)
            .order_by(Dashboard.sector, Dashboard.name)
            .all()
        )

    setores = {}
    for d in dashboards:
        setores.setdefault(d.sector, []).append(d)
    return setores
