from dotenv import load_dotenv
from flask import Flask
from config import Config

from .extensions import db, login_manager, oauth
from .auth import auth_bp
from .routes import main_bp
from .admin import admin_bp
from .models import User


def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    oauth.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    oauth.register(
        name="google",
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
        server_metadata_url=app.config["GOOGLE_DISCOVERY_URL"],
        client_kwargs={"scope": "openid email profile"},
    )

    zoho_client_id = app.config.get("ZOHO_CLIENT_ID")
    zoho_client_secret = app.config.get("ZOHO_CLIENT_SECRET")
    if zoho_client_id and zoho_client_secret:
        accounts_url = (app.config.get("ZOHO_ACCOUNTS_URL") or "https://accounts.zoho.com").rstrip("/")
        oauth.register(
            name="zoho",
            client_id=zoho_client_id,
            client_secret=zoho_client_secret,
            server_metadata_url=f"{accounts_url}/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)  # ✅ aqui

    with app.app_context():
        db.create_all()

    return app
