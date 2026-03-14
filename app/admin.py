import os

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required
from sqlalchemy import case, func

from .extensions import db
from .models import User, Dashboard, UserDashboard
from .admin_guard import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# =========================
# HOME ADMIN (Usuários)
# =========================
@admin_bp.route("/")
@login_required
@admin_required
def index():
    q = request.args.get("q", "").strip()

    # ✅ 1) Admin sempre no topo (0 = admin, 1 = não-admin)
    admin_order = case(
        (User.is_admin == True, 0),
        else_=1
    )

    # ✅ 2) Quem tem nome (não vazio) vem antes (0 = tem nome, 1 = vazio)
    has_name_order = case(
        (
            func.length(func.trim(func.coalesce(User.name, ""))) > 0,
            0
        ),
        else_=1
    )

    users_query = User.query

    if q:
        users_query = users_query.filter(
            (User.name.ilike(f"%{q}%"))
            | (User.email.ilike(f"%{q}%"))
            | (User.sector.ilike(f"%{q}%"))
        )

    users = users_query.order_by(
        admin_order.asc(),
        has_name_order.asc(),
        User.name.asc(),
        User.email.asc()
    ).all()

    return render_template("admin/index.html", users=users, q=q)


# ✅ Criar usuário manualmente (ADM)
@admin_bp.route("/users/new", methods=["POST"])
@login_required
@admin_required
def create_user():
    email = (request.form.get("email") or "").strip().lower()
    name = (request.form.get("name") or "").strip()
    sector = (request.form.get("sector") or "").strip()
    is_admin = True if request.form.get("is_admin") == "on" else False
    active = True if request.form.get("active") == "on" else False

    if not email or "@" not in email:
        flash("Informe um e-mail válido.", "danger")
        return redirect(url_for("admin.index"))

    allowed_domain = current_app.config.get("ALLOWED_EMAIL_DOMAIN")
    if allowed_domain and not email.endswith("@" + allowed_domain):
        flash("E-mail fora do domínio corporativo.", "danger")
        return redirect(url_for("admin.index"))

    exists = User.query.filter_by(email=email).first()
    if exists:
        flash("Este e-mail já está cadastrado.", "warning")
        return redirect(url_for("admin.index"))

    final_name = name if name else ""

    u = User(
        email=email,
        name=final_name,
        sector=sector if sector else None,
        is_admin=is_admin,
        active=active,
    )
    db.session.add(u)
    db.session.commit()

    # conta suporte sempre admin/ativa
    if u.email.lower() == "suporte@carmelhoteis.com.br":
        u.is_admin = True
        u.active = True
        db.session.commit()

    flash("Usuário cadastrado com sucesso.", "success")
    return redirect(url_for("admin.index"))


# ✅ Atualizar campos editáveis (name, email, sector)
@admin_bp.route("/users/<int:user_id>/update", methods=["POST"])
@login_required
@admin_required
def update_user(user_id):
    u = User.query.get_or_404(user_id)

    new_name = (request.form.get("name") or "").strip()
    new_email = (request.form.get("email") or "").strip().lower()
    new_sector = (request.form.get("sector") or "").strip()

    if not new_email or "@" not in new_email:
        flash("E-mail inválido.", "danger")
        return redirect(url_for("admin.index"))

    allowed_domain = current_app.config.get("ALLOWED_EMAIL_DOMAIN")
    if allowed_domain and not new_email.endswith("@" + allowed_domain):
        flash("E-mail fora do domínio corporativo.", "danger")
        return redirect(url_for("admin.index"))

    if new_email != u.email:
        exists = User.query.filter(User.email == new_email, User.id != u.id).first()
        if exists:
            flash("Já existe outro usuário com esse e-mail.", "danger")
            return redirect(url_for("admin.index"))

    u.name = new_name  # pode ser ''
    u.email = new_email
    u.sector = new_sector if new_sector else None

    # conta suporte sempre admin/ativa
    if u.email.lower() == "suporte@carmelhoteis.com.br":
        u.is_admin = True
        u.active = True

    db.session.commit()
    flash("Usuário atualizado com sucesso.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/toggle-admin/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def toggle_admin(user_id):
    u = User.query.get_or_404(user_id)

    if u.email.lower() == "suporte@carmelhoteis.com.br":
        flash("A conta suporte não pode perder admin.", "warning")
        return redirect(url_for("admin.index"))

    u.is_admin = not bool(u.is_admin)
    db.session.commit()
    flash(f"Admin {'ativado' if u.is_admin else 'desativado'} para {u.email}.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/toggle-active/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def toggle_active(user_id):
    u = User.query.get_or_404(user_id)

    if u.email.lower() == "suporte@carmelhoteis.com.br":
        flash("A conta suporte não pode ser inativada.", "warning")
        return redirect(url_for("admin.index"))

    u.active = not bool(u.active)
    db.session.commit()
    flash(f"Usuário {'ativado' if u.active else 'inativado'}: {u.email}.", "success")
    return redirect(url_for("admin.index"))


# ✅ EXCLUIR USUÁRIO
@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    u = User.query.get_or_404(user_id)

    # protege suporte
    if u.email.lower() == "suporte@carmelhoteis.com.br":
        flash("A conta suporte não pode ser excluída.", "warning")
        return redirect(url_for("admin.index"))

    # remove vínculos de permissões
    UserDashboard.query.filter_by(user_id=u.id).delete()

    db.session.delete(u)
    db.session.commit()

    flash("Usuário excluído com sucesso.", "success")
    return redirect(url_for("admin.index"))


# =========================
# PERMISSÕES POR USUÁRIO
# =========================
@admin_bp.route("/users/<int:user_id>", methods=["GET", "POST"])
@login_required
@admin_required
def user_permissions(user_id):
    user = User.query.get_or_404(user_id)

    dashboards = Dashboard.query.order_by(Dashboard.sector.asc(), Dashboard.name.asc()).all()
    allowed_ids = {ud.dashboard_id for ud in user.dashboards}

    sectors = {}
    for d in dashboards:
        sectors.setdefault(d.sector, []).append(d)

    if request.method == "POST":
        selected = request.form.getlist("dashboards")

        UserDashboard.query.filter_by(user_id=user.id).delete()

        for dash_id in selected:
            db.session.add(UserDashboard(user_id=user.id, dashboard_id=int(dash_id)))

        db.session.commit()
        flash("Permissões atualizadas com sucesso.", "success")
        return redirect(url_for("admin.user_permissions", user_id=user.id))

    return render_template(
        "admin/user_permissions.html",
        user=user,
        sectors=sectors,
        allowed_ids=allowed_ids
    )


@admin_bp.route("/users/<int:user_id>/grant-sector", methods=["POST"])
@login_required
@admin_required
def grant_sector(user_id):
    user = User.query.get_or_404(user_id)
    sector = request.form.get("sector", "").strip()

    if not sector:
        flash("Setor inválido.", "danger")
        return redirect(url_for("admin.user_permissions", user_id=user.id))

    dashboards = Dashboard.query.filter_by(sector=sector).all()
    existing = {ud.dashboard_id for ud in user.dashboards}

    added = 0
    for d in dashboards:
        if d.id not in existing:
            db.session.add(UserDashboard(user_id=user.id, dashboard_id=d.id))
            added += 1

    db.session.commit()
    flash(f"Setor {sector} liberado ({added} dashboards adicionados).", "success")
    return redirect(url_for("admin.user_permissions", user_id=user.id))


@admin_bp.route("/users/<int:user_id>/revoke-sector", methods=["POST"])
@login_required
@admin_required
def revoke_sector(user_id):
    user = User.query.get_or_404(user_id)
    sector = request.form.get("sector", "").strip()

    if not sector:
        flash("Setor inválido.", "danger")
        return redirect(url_for("admin.user_permissions", user_id=user.id))

    dashboards_ids = [d.id for d in Dashboard.query.filter_by(sector=sector).all()]
    if dashboards_ids:
        UserDashboard.query.filter(
            UserDashboard.user_id == user.id,
            UserDashboard.dashboard_id.in_(dashboards_ids)
        ).delete(synchronize_session=False)
        db.session.commit()

    flash(f"Setor {sector} removido.", "success")
    return redirect(url_for("admin.user_permissions", user_id=user.id))


# =========================
# DASHBOARDS (CRUD)
# =========================
@admin_bp.route("/dashboards")
@login_required
@admin_required
def dashboards_index():
    q = request.args.get("q", "").strip()
    sector = request.args.get("sector", "").strip()

    query = Dashboard.query

    if sector:
        query = query.filter(Dashboard.sector == sector)

    if q:
        query = query.filter(
            (Dashboard.name.ilike(f"%{q}%")) |
            (Dashboard.slug.ilike(f"%{q}%")) |
            (Dashboard.url.ilike(f"%{q}%"))
        )

    dashboards = query.order_by(Dashboard.sector.asc(), Dashboard.name.asc()).all()

    sectors = [row[0] for row in db.session.query(Dashboard.sector).distinct().order_by(Dashboard.sector.asc()).all()]

    return render_template(
        "admin/dashboards.html",
        dashboards=dashboards,
        sectors=sectors,
        q=q,
        sector=sector
    )


@admin_bp.route("/dashboards/new", methods=["GET", "POST"])
@login_required
@admin_required
def dashboards_new():
    if request.method == "POST":
        sector = request.form.get("sector", "").strip()
        name = request.form.get("name", "").strip()
        slug = request.form.get("slug", "").strip()
        url = request.form.get("url", "").strip()

        if not sector or not name or not slug or not url:
            flash("Preencha todos os campos.", "danger")
            return redirect(url_for("admin.dashboards_new"))

        exists = Dashboard.query.filter_by(slug=slug).first()
        if exists:
            flash("Slug já existe. Use outro.", "danger")
            return redirect(url_for("admin.dashboards_new"))

        d = Dashboard(sector=sector, name=name, slug=slug, url=url)
        db.session.add(d)
        db.session.commit()

        flash("Dashboard criado com sucesso.", "success")
        return redirect(url_for("admin.dashboards_index"))

    return render_template("admin/dashboard_form.html", mode="new", dash=None)


@admin_bp.route("/dashboards/<int:dash_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def dashboards_edit(dash_id):
    d = Dashboard.query.get_or_404(dash_id)

    if request.method == "POST":
        sector = request.form.get("sector", "").strip()
        name = request.form.get("name", "").strip()
        slug = request.form.get("slug", "").strip()
        url = request.form.get("url", "").strip()

        if not sector or not name or not slug or not url:
            flash("Preencha todos os campos.", "danger")
            return redirect(url_for("admin.dashboards_edit", dash_id=d.id))

        if slug != d.slug:
            exists = Dashboard.query.filter_by(slug=slug).first()
            if exists:
                flash("Slug já existe. Use outro.", "danger")
                return redirect(url_for("admin.dashboards_edit", dash_id=d.id))

        d.sector = sector
        d.name = name
        d.slug = slug
        d.url = url

        db.session.commit()
        flash("Dashboard atualizado com sucesso.", "success")
        return redirect(url_for("admin.dashboards_index"))

    return render_template("admin/dashboard_form.html", mode="edit", dash=d)


@admin_bp.route("/dashboards/<int:dash_id>/delete", methods=["POST"])
@login_required
@admin_required
def dashboards_delete(dash_id):
    d = Dashboard.query.get_or_404(dash_id)

    UserDashboard.query.filter_by(dashboard_id=d.id).delete()
    db.session.delete(d)
    db.session.commit()

    flash("Dashboard removido com sucesso.", "success")
    return redirect(url_for("admin.dashboards_index"))


@admin_bp.route("/dashboards/import", methods=["GET", "POST"])
@login_required
@admin_required
def dashboards_import():
    if request.method == "POST":
        action = (request.form.get("action") or "manual").strip().lower()
        mode = (request.form.get("mode") or "sync").strip().lower()
        remove_missing = request.form.get("remove_missing") == "on"

        def parse_rows(rows):
            data = {}
            errors = 0
            duplicates = 0
            for row in rows:
                if not row:
                    continue
                values = [str(v).strip() for v in row]
                if len(values) < 4:
                    errors += 1
                    continue
                sector, name, slug, url = values[0], values[1], values[2], values[3]
                if not (sector and name and slug and url):
                    errors += 1
                    continue
                if slug in data:
                    duplicates += 1
                data[slug] = {
                    "sector": sector,
                    "name": name,
                    "slug": slug,
                    "url": url,
                }
            return data, errors, duplicates

        def fetch_sheet_rows():
            creds_path = current_app.config.get("GOOGLE_SHEETS_CREDENTIALS_PATH")
            sheet_id = current_app.config.get("GOOGLE_SHEETS_ID")
            sheet_tab = current_app.config.get("GOOGLE_SHEETS_TAB")

            if not creds_path or not sheet_id or not sheet_tab:
                raise ValueError("Configuração do Google Sheets incompleta.")
            if not os.path.exists(creds_path):
                raise ValueError("Arquivo de credenciais não encontrado.")

            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            creds = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
            )
            service = build("sheets", "v4", credentials=creds, cache_discovery=False)
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=sheet_tab,
            ).execute()
            return result.get("values", [])

        created = 0
        updated = 0
        removed = 0
        errors = 0
        duplicates = 0
        data_by_slug = {}

        if action == "sheet":
            try:
                rows = fetch_sheet_rows()
            except Exception as exc:
                flash(f"Erro ao ler a planilha: {exc}", "danger")
                return redirect(url_for("admin.dashboards_import"))

            if rows:
                header = [str(v).strip().lower() for v in rows[0][:4]]
                if header == ["setor", "nome", "slug", "url"]:
                    rows = rows[1:]
            data_by_slug, errors, duplicates = parse_rows(rows)
        else:
            raw = request.form.get("bulk", "").strip()
            if not raw:
                flash("Cole pelo menos 1 linha.", "danger")
                return redirect(url_for("admin.dashboards_import"))

            lines = [l.strip() for l in raw.splitlines() if l.strip()]
            rows = []
            for line in lines:
                if "|" in line:
                    parts = [p.strip() for p in line.split("|")]
                elif ";" in line:
                    parts = [p.strip() for p in line.split(";")]
                else:
                    parts = [p.strip() for p in line.split("\t")]
                rows.append(parts)

            if rows:
                header = [str(v).strip().lower() for v in rows[0][:4]]
                if header == ["setor", "nome", "slug", "url"]:
                    rows = rows[1:]
            data_by_slug, errors, duplicates = parse_rows(rows)

        if not data_by_slug:
            flash("Nenhuma linha válida encontrada.", "danger")
            return redirect(url_for("admin.dashboards_import"))

        if mode == "replace":
            removed = Dashboard.query.count()
            UserDashboard.query.delete(synchronize_session=False)
            Dashboard.query.delete(synchronize_session=False)
            for data in data_by_slug.values():
                db.session.add(Dashboard(**data))
                created += 1
        else:
            slugs = list(data_by_slug.keys())
            existing = {
                d.slug: d
                for d in Dashboard.query.filter(Dashboard.slug.in_(slugs)).all()
            }

            for slug, data in data_by_slug.items():
                if slug in existing:
                    d = existing[slug]
                    d.sector = data["sector"]
                    d.name = data["name"]
                    d.url = data["url"]
                    updated += 1
                else:
                    db.session.add(Dashboard(**data))
                    created += 1

            if remove_missing:
                to_delete = Dashboard.query.filter(~Dashboard.slug.in_(slugs)).all()
                removed = len(to_delete)
                if removed:
                    del_ids = [d.id for d in to_delete]
                    UserDashboard.query.filter(
                        UserDashboard.dashboard_id.in_(del_ids)
                    ).delete(synchronize_session=False)
                    for d in to_delete:
                        db.session.delete(d)

        db.session.commit()
        flash(
            "Importação finalizada. "
            f"Criados {created}, Atualizados {updated}, Removidos {removed}, "
            f"Inválidas {errors}, Duplicadas {duplicates}.",
            "success"
        )
        return redirect(url_for("admin.dashboards_index"))

    return render_template("admin/dashboard_import.html")
