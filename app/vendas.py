from datetime import date, timedelta

from flask import Blueprint, flash, render_template, request
from flask_login import login_required

from .db_carmel import get_connection

vendas_bp = Blueprint("vendas", __name__, url_prefix="/vendas")

_HOTEIS = ["CUMBUCO", "TAIBA", "CHARME", "MAGNA"]
_PAGE_SIZE = 50

_TIPOS_DISCREPANCIA = {
    "pdv_sem_nfe":      "PDV sem NF-e",
    "nfe_sem_pdv":      "NF-e sem PDV",
    "nfe_sem_fiscal":   "NF-e sem Fiscal",
    "valor_divergente": "Divergência de Valor",
    "pendente_sefaz":   "Pendente SEFAZ",
}


def _parse_filters():
    hoje = date.today()
    hotel = request.args.get("hotel", "")
    tipo = request.args.get("tipo", "")
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
    return hotel, tipo, data_inicio, data_fim, pagina


def _count_discrepancias(cur, hotel, data_inicio, data_fim):
    hotel_clause = "AND p.hotel = %s" if hotel else ""
    hotel_clause_v = "AND hotel = %s" if hotel else ""
    hotel_param = [hotel] if hotel else []

    counts = {}

    # pdv_sem_nfe
    cur.execute(
        f"""
        SELECT COUNT(*) AS n
        FROM carmel.v_pdv_notas p
        LEFT JOIN carmel.nfe_raw_xmls n ON n.nota_id = p.chave_nfe
        WHERE n.nota_id IS NULL
          AND p.chave_nfe IS NOT NULL
          AND p.data_venda BETWEEN %s AND %s
          {hotel_clause}
        """,
        [data_inicio, data_fim] + hotel_param,
    )
    counts["pdv_sem_nfe"] = cur.fetchone()["n"]

    # nfe_sem_pdv
    cur.execute(
        f"""
        SELECT COUNT(*) AS n
        FROM carmel.v_nfe_notas
        WHERE tem_pdv = FALSE
          AND status_sefaz = '100'
          AND cancelada = FALSE
          AND data_emissao::date BETWEEN %s AND %s
          {hotel_clause_v}
        """,
        [data_inicio, data_fim] + hotel_param,
    )
    counts["nfe_sem_pdv"] = cur.fetchone()["n"]

    # nfe_sem_fiscal
    cur.execute(
        f"""
        SELECT COUNT(*) AS n
        FROM carmel.v_vendas_notas
        WHERE tem_fiscal = FALSE AND status = 'Autorizada'
          AND data_emissao::date BETWEEN %s AND %s
          {hotel_clause_v}
        """,
        [data_inicio, data_fim] + hotel_param,
    )
    counts["nfe_sem_fiscal"] = cur.fetchone()["n"]

    # valor_divergente
    cur.execute(
        f"""
        SELECT COUNT(*) AS n
        FROM carmel.v_nfe_notas
        WHERE tem_pdv AND ABS(valor_total - valor_pdv) > 0.01
          AND data_emissao::date BETWEEN %s AND %s
          {hotel_clause_v}
        """,
        [data_inicio, data_fim] + hotel_param,
    )
    counts["valor_divergente"] = cur.fetchone()["n"]

    # pendente_sefaz
    cur.execute(
        f"""
        SELECT COUNT(*) AS n
        FROM carmel.v_nfe_notas
        WHERE cancelada = FALSE
          AND status_sefaz != '100'
          AND data_emissao::date BETWEEN %s AND %s
          {hotel_clause_v}
        """,
        [data_inicio, data_fim] + hotel_param,
    )
    counts["pendente_sefaz"] = cur.fetchone()["n"]

    return counts


def _query_discrepancias(cur, hotel, tipo, data_inicio, data_fim, pagina):
    hotel_clause_p = "AND p.hotel = %s" if hotel else ""
    hotel_clause_v = "AND hotel = %s" if hotel else ""
    hotel_param = [hotel] if hotel else []

    base_params = [data_inicio, data_fim] + hotel_param

    if tipo == "pdv_sem_nfe":
        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM carmel.v_pdv_notas p
            LEFT JOIN carmel.nfe_raw_xmls n ON n.nota_id = p.chave_nfe
            WHERE n.nota_id IS NULL
              AND p.chave_nfe IS NOT NULL
              AND p.data_venda BETWEEN %s AND %s
              {hotel_clause_p}
        """
        data_sql = f"""
            SELECT p.chave_nfe, p.hotel, p.data_venda AS data, p.numero_nota,
                   p.subtotal_1 AS valor, p.ponto_venda, p.quarto, p.garcom
            FROM carmel.v_pdv_notas p
            LEFT JOIN carmel.nfe_raw_xmls n ON n.nota_id = p.chave_nfe
            WHERE n.nota_id IS NULL
              AND p.chave_nfe IS NOT NULL
              AND p.data_venda BETWEEN %s AND %s
              {hotel_clause_p}
            ORDER BY p.data_venda DESC
            LIMIT %s OFFSET %s
        """
    elif tipo == "nfe_sem_pdv":
        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM carmel.v_nfe_notas
            WHERE tem_pdv = FALSE
              AND status_sefaz = '100'
              AND cancelada = FALSE
              AND data_emissao::date BETWEEN %s AND %s
              {hotel_clause_v}
        """
        data_sql = f"""
            SELECT nota_id, hotel, data_emissao::date AS data, numero_nota,
                   serie, valor_total, ponto_venda
            FROM carmel.v_nfe_notas
            WHERE tem_pdv = FALSE
              AND status_sefaz = '100'
              AND cancelada = FALSE
              AND data_emissao::date BETWEEN %s AND %s
              {hotel_clause_v}
            ORDER BY data_emissao DESC
            LIMIT %s OFFSET %s
        """
    elif tipo == "nfe_sem_fiscal":
        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM carmel.v_vendas_notas
            WHERE tem_fiscal = FALSE AND status = 'Autorizada'
              AND data_emissao::date BETWEEN %s AND %s
              {hotel_clause_v}
        """
        data_sql = f"""
            SELECT nota_id, hotel, data_emissao::date AS data, numero_nota,
                   serie, valor_total, tem_pdv
            FROM carmel.v_vendas_notas
            WHERE tem_fiscal = FALSE AND status = 'Autorizada'
              AND data_emissao::date BETWEEN %s AND %s
              {hotel_clause_v}
            ORDER BY data_emissao DESC
            LIMIT %s OFFSET %s
        """
    elif tipo == "valor_divergente":
        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM carmel.v_nfe_notas
            WHERE tem_pdv AND ABS(valor_total - valor_pdv) > 0.01
              AND data_emissao::date BETWEEN %s AND %s
              {hotel_clause_v}
        """
        data_sql = f"""
            SELECT v.nota_id, v.hotel, v.data_emissao::date AS data, v.numero_nota,
                   v.valor_total, v.valor_pdv,
                   v.valor_total - v.valor_pdv AS diferenca,
                   v.ponto_venda,
                   p.data->>'Invoice Data Info 5' AS quarto
            FROM carmel.v_nfe_notas v
            LEFT JOIN carmel.pdv_raw_notas p USING (nota_id)
            WHERE v.tem_pdv AND ABS(v.valor_total - v.valor_pdv) > 0.01
              AND v.data_emissao::date BETWEEN %s AND %s
              {"AND v.hotel = %s" if hotel else ""}
            ORDER BY ABS(v.valor_total - v.valor_pdv) DESC
            LIMIT %s OFFSET %s
        """
    else:  # pendente_sefaz
        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM carmel.v_nfe_notas
            WHERE cancelada = FALSE
              AND status_sefaz != '100'
              AND data_emissao::date BETWEEN %s AND %s
              {hotel_clause_v}
        """
        data_sql = f"""
            SELECT nota_id, hotel, data_emissao::date AS data, numero_nota,
                   serie, valor_total, status_sefaz, tem_pdv
            FROM carmel.v_nfe_notas
            WHERE cancelada = FALSE
              AND status_sefaz != '100'
              AND data_emissao::date BETWEEN %s AND %s
              {hotel_clause_v}
            ORDER BY data_emissao DESC
            LIMIT %s OFFSET %s
        """

    cur.execute(count_sql, base_params)
    total = cur.fetchone()["total"]

    offset = (pagina - 1) * _PAGE_SIZE
    cur.execute(data_sql, base_params + [_PAGE_SIZE, offset])
    rows = cur.fetchall()

    return rows, total


@vendas_bp.route("/")
@login_required
def index():
    hotel, tipo, data_inicio, data_fim, pagina = _parse_filters()

    contagens = {t: 0 for t in _TIPOS_DISCREPANCIA}
    rows = []
    total_rows = 0

    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                contagens = _count_discrepancias(cur, hotel, data_inicio, data_fim)

                # Se nenhum tipo foi selecionado, escolhe o primeiro com dados
                if not tipo or tipo not in _TIPOS_DISCREPANCIA:
                    tipo = next(
                        (t for t in _TIPOS_DISCREPANCIA if contagens[t] > 0),
                        list(_TIPOS_DISCREPANCIA.keys())[0],
                    )

                rows, total_rows = _query_discrepancias(
                    cur, hotel, tipo, data_inicio, data_fim, pagina
                )
        finally:
            conn.close()
    except Exception as exc:
        flash(f"Não foi possível carregar os dados de vendas. ({exc})", "danger")
        if not tipo or tipo not in _TIPOS_DISCREPANCIA:
            tipo = list(_TIPOS_DISCREPANCIA.keys())[0]

    total_paginas = max(1, (total_rows + _PAGE_SIZE - 1) // _PAGE_SIZE)

    return render_template(
        "vendas/index.html",
        contagens=contagens,
        rows=rows,
        tipo=tipo,
        tipos=_TIPOS_DISCREPANCIA,
        hoteis=_HOTEIS,
        filtros={
            "hotel": hotel,
            "data_inicio": data_inicio.isoformat(),
            "data_fim": data_fim.isoformat(),
        },
        pagina=pagina,
        total_paginas=total_paginas,
        total_rows=total_rows,
    )
