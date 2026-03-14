from flask_login import UserMixin
from .extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    active = db.Column(db.Boolean, default=True)

    # Admin
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    # ✅ NOVO: Setor do usuário (OPCIONAL)
    sector = db.Column(db.String(120), nullable=True)

    dashboards = db.relationship("UserDashboard", back_populates="user")


class Dashboard(db.Model):
    __tablename__ = "dashboard"

    id = db.Column(db.Integer, primary_key=True)
    sector = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    url = db.Column(db.String(500), nullable=False)

    users = db.relationship("UserDashboard", back_populates="dashboard")


class UserDashboard(db.Model):
    __tablename__ = "user_dashboard"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    dashboard_id = db.Column(db.Integer, db.ForeignKey("dashboard.id"))

    user = db.relationship("User", back_populates="dashboards")
    dashboard = db.relationship("Dashboard", back_populates="users")
