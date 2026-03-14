from app import create_app
from app.extensions import db
from app.models import Dashboard

app = create_app()


def seed_dashboards():
    # coloque aqui os links certos do BI do GLPI
    dashboards_data = [
        {
            "sector": "TI",
            "name": "GLPI - Operacional",
            "slug": "glpi-operacional",
            "url": "https://app.powerbi.com/view?r=eyJrIjoiODU1NzA3YWItMGRiMy00YzhiLTgyODItNjE1YjdmZGY0MDcxIiwidCI6IjA0OGIzYWI0LWM4MTUtNDM2Zi04MzRkLTU2OTY3MzQ3YzI0ZCJ9"
        },
        {
            "sector": "TI",
            "name": "GLPI - Gerencial",
            "slug": "glpi-gerencial",
            "url": "https://app.powerbi.com/view?r=eyJrIjoiYjNjYzFkNzUtOTJkMy00ZmYzLThiMWUtNTdkOWZiZjliYTU0IiwidCI6IjA0OGIzYWI0LWM4MTUtNDM2Zi04MzRkLTU2OTY3MzQ3YzI0ZCJ9"
        },
    ]

    for data in dashboards_data:
        existe = Dashboard.query.filter_by(slug=data["slug"]).first()
        if not existe:
            dash = Dashboard(
                sector=data["sector"],
                name=data["name"],
                slug=data["slug"],
                url=data["url"],
            )
            db.session.add(dash)

    db.session.commit()
    print("Dashboards cadastrados / atualizados com sucesso!")


if __name__ == "__main__":
    with app.app_context():
        seed_dashboards()
