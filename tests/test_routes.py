"""
Testes das rotas principais da intranet (área BI e dashboards).
"""

import pytest
from tests.conftest import login_as


def test_bi_autenticado_retorna_200(app, client, regular_user):
    login_as(client, regular_user.id)
    r = client.get("/bi/")
    assert r.status_code == 200


def test_dashboard_inexistente_retorna_404(app, client, regular_user):
    login_as(client, regular_user.id)
    r = client.get("/bi/TI/inexistente/")
    assert r.status_code == 404


def test_usuario_sem_permissao_retorna_403(app, client, regular_user):
    from app.models import Dashboard
    from app.extensions import db

    with app.app_context():
        dash = Dashboard(
            sector="TI",
            name="Painel TI",
            slug="painel-ti",
            url="https://metabase.carmel.local/dashboard/1",
        )
        db.session.add(dash)
        db.session.commit()

    login_as(client, regular_user.id)
    r = client.get("/bi/TI/painel-ti/")
    assert r.status_code == 403


def test_admin_acessa_dashboard_sem_permissao_explicita(app, client, admin_user):
    from app.models import Dashboard
    from app.extensions import db

    with app.app_context():
        dash = Dashboard(
            sector="FINANCEIRO",
            name="Receita Bruta",
            slug="receita-bruta",
            url="https://metabase.carmel.local/dashboard/2",
        )
        db.session.add(dash)
        db.session.commit()

    login_as(client, admin_user.id)
    r = client.get("/bi/FINANCEIRO/receita-bruta/")
    assert r.status_code == 200


def test_bi_sem_login_redireciona(client):
    r = client.get("/bi/", follow_redirects=False)
    assert r.status_code == 302
