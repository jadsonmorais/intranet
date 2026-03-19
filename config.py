import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY environment variable is required")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///intranet_carmel.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
    GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

    ZOHO_ACCOUNTS_URL = os.environ.get("ZOHO_ACCOUNTS_URL", "https://accounts.zoho.com")
    ZOHO_CLIENT_ID = os.environ.get("ZOHO_CLIENT_ID")
    ZOHO_CLIENT_SECRET = os.environ.get("ZOHO_CLIENT_SECRET")

    GOOGLE_SHEETS_CREDENTIALS_PATH = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_PATH")
    GOOGLE_SHEETS_ID = os.environ.get("GOOGLE_SHEETS_ID")
    GOOGLE_SHEETS_TAB = os.environ.get("GOOGLE_SHEETS_TAB")

    # 👇 NOVO
    SERVER_NAME = os.environ.get("SERVER_NAME")  # ex: intranet.cm
    PREFERRED_URL_SCHEME = "https"

    CARMEL_DB_URL = os.environ.get("CARMEL_DB_URL")

    SUPERADMIN_EMAIL = os.environ.get("SUPERADMIN_EMAIL", "suporte@carmelhoteis.com.br")

    # ✅ agora aceita múltiplos domínios
    ALLOWED_EMAIL_DOMAINS = [
        "carmelhoteis.com.br",
        "carmelcharme.com.br",
        "carmelcumbuco.com.br",
        "carmeltaiba.com.br",
        "magnapraiahotel.com.br",
        "magnaloc.com.br",
    ]
