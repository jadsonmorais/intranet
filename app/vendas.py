from datetime import date, timedelta

from flask import Blueprint, flash, render_template, request
from flask_login import login_required

from .db_carmel import get_connection

vendas_bp = Blueprint("vendas", __name__, url_prefix="/vendas")

_HOTEIS = ["CUMBUCO", "TAIBA", "CHARME", "MAGNA"]
_STATUS = ["Autorizada", "Cancelada", "Pendente SEFAZ"]
_PAGE_SIZE = 50


def _parse_filters():
    hoje = date.today()
    hotel = request.args.get("hotel", "")
    status = request.args.get("status", "")
    try:
        data_inicio = date.fromisoformat(request.args.get("data_inicio", ""))
    except ValueError:
        data_inicio = hoje - timedelta(days=30)
    try:
        data_fim = date.fromisoformat(request.args.get("data_fim", ""))
    except ValueError:
        data_fim = hoje
    try:
        pagina = max(1, int(request.args.get("pagina", 1)))
    except ValueError:
        pagina = 1
    return hotel, status, data_inicio, data_fim, pagina


def _build_where(hotel, status, data_inicio, data_fim):
    clauses = ["data_emissao::date BETWEEN %s AND %s"]
    params = [data_inicio, data_fim]
    if hotel:
        clauses.append("hotel = %s")
        params.append(hotel)
    if status:
        clauses.append("status = %s")
        params.append(status)
    return " AND ".join(clauses), params


def _query_kpis(cur, hotel, status, data_inicio, data_fim):
    where, params = _build_where(hotel, status, data_inicio, data_fim)
    cur.execute(
        f"""
        SELECT
            COUNT(*)                                                AS total_notas,
            COUNT(*) FILTER (WHERE status = 'Autorizada')          AS autorizadas,
            COUNT(*) FILTER (WHERE status = 'Cancelada')           AS canceladas,
            COALESCE(SUM(valor_total) FILTER (WHERE status != 'Cancelada'), 0) AS valor_total
        FROM carmel.v_vendas_notas
        WHERE {where}
        """,
        params,
    )
    return cur.fetchone()


def _query_notas(cur, hotel, status, data_inicio, data_fim, pagina):
    where, params = _build_where(hotel, status, data_inicio, data_fim)
    cur.execute(
        f"SELECT COUNT(*) AS total FROM carmel.v_vendas_notas WHERE {where}",
        params,
    )
    total = cur.fetchone()["total"]

    offset = (pagina - 1) * _PAGE_SIZE
    cur.execute(
        f"""
        SELECT
            nota_id, hotel, data_emissao::date AS data, numero_nota, serie,
            valor_total, status, tem_pdv, tem_fiscal, quarto, garcom, ponto_venda
        FROM carmel.v_vendas_notas
        WHERE {where}
        ORDER BY data_emissao DESC
        LIMIT %s OFFSET %s
        """,
        params + [_PAGE_SIZE, offset],
    )
    notas = cur.fetchall()
    return notas, total


@vendas_bp.route("/")
@login_required
def index():
    hotel, status, data_inicio, data_fim, pagina = _parse_filters()

    kpis = {"total_notas": 0, "autorizadas": 0, "canceladas": 0, "valor_total": 0}
    notas = []
    total_notas = 0

    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                kpis = _query_kpis(cur, hotel, status, data_inicio, data_fim)
                notas, total_notas = _query_notas(cur, hotel, status, data_inicio, data_fim, pagina)
        finally:
            conn.close()
    except Exception as exc:
        flash(f"Não foi possível carregar os dados de vendas. ({exc})", "danger")

    total_paginas = max(1, (total_notas + _PAGE_SIZE - 1) // _PAGE_SIZE)

    return render_template(
        "vendas/index.html",
        kpis=kpis,
        notas=notas,
        hoteis=_HOTEIS,
        status_opts=_STATUS,
        filtros={
            "hotel": hotel,
            "status": status,
            "data_inicio": data_inicio.isoformat(),
            "data_fim": data_fim.isoformat(),
        },
        pagina=pagina,
        total_paginas=total_paginas,
        total_notas=total_notas,
    )
