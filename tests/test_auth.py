"""
Testes das rotas de autenticação OAuth da intranet.
Mock do OAuth para não depender de Google/Zoho em CI.
"""

import pytest
from tests.conftest import login_as


def test_login_page_retorna_200(client):
    r = client.get("/auth/login")
    assert r.status_code == 200


def test_bi_sem_login_redireciona_para_login(client):
    r = client.get("/bi/", follow_redirects=False)
    assert r.status_code == 302
    assert "/auth/login" in r.headers["Location"]


def test_dominio_nao_autorizado_redireciona_para_login(app, client):
    from app.extensions import oauth

    with app.app_context():
        original_token = oauth.google.authorize_access_token
        original_userinfo = oauth.google.userinfo
        oauth.google.authorize_access_token = lambda: {}
        oauth.google.userinfo = lambda: {"email": "invasor@gmail.com", "name": "Invasor"}
        try:
            r = client.get("/auth/authorize", follow_redirects=False)
            assert r.status_code == 302
            assert "/bi/" not in r.headers.get("Location", "")
        finally:
            oauth.google.authorize_access_token = original_token
            oauth.google.userinfo = original_userinfo


def test_usuario_nao_cadastrado_redireciona_para_login(app, client):
    from app.extensions import oauth

    with app.app_context():
        original_token = oauth.google.authorize_access_token
        original_userinfo = oauth.google.userinfo
        oauth.google.authorize_access_token = lambda: {}
        # domínio autorizado, mas usuário não existe no banco
        oauth.google.userinfo = lambda: {
            "email": "desconhecido@carmelhoteis.com.br",
            "name": "Desconhecido",
        }
        try:
            r = client.get("/auth/authorize", follow_redirects=False)
            assert r.status_code == 302
            assert "/auth/login" in r.headers.get("Location", "")
        finally:
            oauth.google.authorize_access_token = original_token
            oauth.google.userinfo = original_userinfo


def test_usuario_inativo_redireciona_para_login(app, client):
    from app.extensions import oauth
    from app.models import User

    with app.app_context():
        # cria usuário inativo
        inactive = User(
            email="inativo@carmelhoteis.com.br",
            name="Inativo",
            is_admin=False,
            active=False,
        )
        from app.extensions import db
        db.session.add(inactive)
        db.session.commit()

        original_token = oauth.google.authorize_access_token
        original_userinfo = oauth.google.userinfo
        oauth.google.authorize_access_token = lambda: {}
        oauth.google.userinfo = lambda: {
            "email": "inativo@carmelhoteis.com.br",
            "name": "Inativo",
        }
        try:
            r = client.get("/auth/authorize", follow_redirects=False)
            assert r.status_code == 302
            assert "/auth/login" in r.headers.get("Location", "")
        finally:
            oauth.google.authorize_access_token = original_token
            oauth.google.userinfo = original_userinfo


def test_logout_redireciona_para_login(app, client, regular_user):
    login_as(client, regular_user.id)
    r = client.get("/auth/logout", follow_redirects=False)
    assert r.status_code == 302
    assert "/auth/login" in r.headers.get("Location", "")
