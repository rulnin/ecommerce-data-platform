"""Create the local Metabase account, warehouse connection and starter dashboard."""

import argparse
from pathlib import Path

import requests
from dotenv import dotenv_values

from scripts.verify_phase9 import QUESTIONS

ROOT = Path(__file__).resolve().parents[1]
NAME = "E-commerce overview"
DESCRIPTION = (
    "Historical Olist snapshot (2016–2018). Delivered item value is a sales proxy "
    "excluding freight, refunds and fees. Payments are tender amounts. USD has partial "
    "FX coverage. Source: Brazilian E-Commerce Public Dataset by Olist (Kaggle), "
    "CC BY-NC-SA 4.0; adapted through typed joins and aggregation."
)
CHARTS = {
    "02_monthly_sales": ("line", "purchase_month", "delivered_item_value_brl"),
    "03_top_categories": ("bar", "category", "delivered_item_value_brl"),
    "04_buyer_states": ("bar", "buyer_state", "delivered_item_value_brl"),
    "05_payment_mix": ("bar", "payment_type", "payment_value_brl"),
    "07_top_sellers": ("bar", "seller_rank", "delivered_item_value_brl"),
}

TITLES = {
    "01_overview": "Snapshot overview",
    "02_monthly_sales": "Monthly delivered sales (BRL)",
    "03_top_categories": "Top product categories (BRL)",
    "04_buyer_states": "Sales by buyer state (BRL)",
    "05_payment_mix": "Payment methods (BRL)",
    "06_repeat_buyers": "Repeat buyers",
    "07_top_sellers": "Top sellers (BRL)",
    "08_fx_coverage": "Exchange-rate coverage",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update-layout",
        action="store_true",
        help="Apply spacious layout and short titles to the existing starter dashboard",
    )
    args = parser.parse_args()
    config = dotenv_values(ROOT / ".env")
    base = "http://127.0.0.1:" + config.get("METABASE_PORT", "3000")
    session = requests.Session()

    def call(method, path, **kwargs):
        response = session.request(method, base + "/api" + path, timeout=120, **kwargs)
        if not response.ok:
            # Responses to setup/connection errors can contain credentials.
            raise RuntimeError(f"Metabase {method} {path} failed (HTTP {response.status_code})")
        return response.json() if response.content else None

    properties = call("GET", "/session/properties")
    if properties.get("setup-token"):
        login = call(
            "POST",
            "/setup",
            json={
                "token": properties["setup-token"],
                "user": {
                    "email": config["METABASE_ADMIN_EMAIL"],
                    "first_name": "Local",
                    "last_name": "Admin",
                    "password": config["METABASE_ADMIN_PASSWORD"],
                },
                "prefs": {"site_name": "E-commerce analytics", "site_locale": "en"},
            },
        )
    else:
        login = call(
            "POST",
            "/session",
            json={
                "username": config["METABASE_ADMIN_EMAIL"],
                "password": config["METABASE_ADMIN_PASSWORD"],
            },
        )
    session.headers["X-Metabase-Session"] = login["id"]
    databases = call("GET", "/database")["data"]
    database = next((d for d in databases if d["name"] == "E-commerce warehouse"), None)
    if database is None:
        database = call(
            "POST",
            "/database",
            json={
                "name": "E-commerce warehouse",
                "engine": "postgres",
                "details": {
                    "host": "postgres",
                    "port": 5432,
                    "dbname": config["POSTGRES_DB"],
                    "user": "metabase_reporting",
                    "password": config["METABASE_REPORTING_PASSWORD"],
                    "ssl": False,
                    "schema-filters-type": "inclusion",
                    "schema-filters-patterns": "published",
                },
            },
        )
    dashboards = call("GET", "/dashboard")
    dashboard = next((d for d in dashboards if d["name"] == NAME), None)
    if dashboard is None:
        dashboard = call("POST", "/dashboard", json={"name": NAME, "description": DESCRIPTION})
    dashboard = call("GET", f"/dashboard/{dashboard['id']}")
    # Preserve a previously configured/customized dashboard on repeated setup.
    if not dashboard.get("dashcards"):
        existing = call("GET", "/card")
        cards = []
        for index, (filename, question) in enumerate(QUESTIONS):
            card_name = TITLES[filename]
            card = next(
                (c for c in existing if c["name"] in (card_name, "E-commerce: " + question)), None
            )
            if card is None:
                display, dimension, metric = CHARTS.get(filename, ("table", None, None))
                settings = (
                    {"graph.dimensions": [dimension], "graph.metrics": [metric]}
                    if dimension
                    else {}
                )
                card = call(
                    "POST",
                    "/card",
                    json={
                        "name": card_name,
                        "description": question + "\n\n" + DESCRIPTION,
                        "dataset_query": {
                            "database": database["id"],
                            "type": "native",
                            "native": {
                                "query": (ROOT / "sql/analytics" / (filename + ".sql")).read_text()
                            },
                        },
                        "display": display,
                        "visualization_settings": settings,
                    },
                )
            cards.append(
                {
                    "id": -(index + 1),
                    "card_id": card["id"],
                    "row": index * 7,
                    "col": 0,
                    "size_x": 24,
                    "size_y": 7,
                    "parameter_mappings": [],
                }
            )
        call("PUT", f"/dashboard/{dashboard['id']}", json={"dashcards": cards, "width": "full"})
    if args.update_layout:
        dashboard = call("GET", f"/dashboard/{dashboard['id']}")
        cards = []
        allowed = {
            "id",
            "card_id",
            "row",
            "col",
            "size_x",
            "size_y",
            "series",
            "parameter_mappings",
            "visualization_settings",
            "dashboard_tab_id",
        }
        for index, item in enumerate(dashboard["dashcards"]):
            card = item.get("card") or {}
            query = card.get("dataset_query", {}).get("native", {}).get("query")
            for filename, question in QUESTIONS:
                if (
                    card.get("name") in (TITLES[filename], "E-commerce: " + question)
                    or query == (ROOT / "sql/analytics" / (filename + ".sql")).read_text()
                ):
                    call("PUT", f"/card/{card['id']}", json={"name": TITLES[filename]})
                    break
            layout = {key: value for key, value in item.items() if key in allowed}
            layout.update(row=index * 7, col=0, size_x=24, size_y=7)
            cards.append(layout)
        call("PUT", f"/dashboard/{dashboard['id']}", json={"dashcards": cards, "width": "full"})
    call("DELETE", "/session", json={"session_id": login["id"]})
    print(f"Dashboard ready: {base}/dashboard/{dashboard['id']}#refresh=300")
    print("Local admin credentials: METABASE_ADMIN_EMAIL / METABASE_ADMIN_PASSWORD in .env")


if __name__ == "__main__":
    main()
