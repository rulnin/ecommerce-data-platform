"""Read-only business queries and aggregate report from a validated publication."""

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal

from psycopg.rows import dict_row

from scripts.dbt import ROOT
from src.common.config import load_settings
from src.common.db import connection

QUESTIONS = (
    ("01_overview", "What are the snapshot volume and delivered item value?"),
    ("02_monthly_sales", "How do delivered sales vary by purchase month?"),
    ("03_top_categories", "Which categories contribute the most delivered item value?"),
    ("04_buyer_states", "Which buyer states contribute delivered item value?"),
    ("05_payment_mix", "How are tender amounts distributed by payment type?"),
    ("06_repeat_buyers", "What fraction of people have repeat delivered orders?"),
    ("07_top_sellers", "Which anonymous seller ranks contribute the most sales?"),
    ("08_fx_coverage", "How much of the snapshot has stored historical FX coverage?"),
)


def execute_queries(settings):
    results, hashes = {}, {}
    with connection(settings) as db:
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        status = db.execute(
            "SELECT run_id::text,status FROM metadata.quality_runs ORDER BY finished_at DESC NULLS LAST LIMIT 1"
        ).fetchone()
        if not status or status[1] != "published":
            raise RuntimeError(
                "Latest quality attempt is not published; inspect the quality report"
            )
        for name, _ in QUESTIONS:
            path = ROOT / "sql/analytics" / (name + ".sql")
            query = path.read_text()
            hashes[name] = hashlib.sha256(query.encode()).hexdigest()
            with db.cursor(row_factory=dict_row) as cur:
                cur.execute(query)
                results[name] = cur.fetchall()
        # Independent raw baselines, never an item-to-payment many-to-many join.
        raw = db.execute("""SELECT
          (SELECT count(*) FROM raw.orders), (SELECT count(*) FROM raw.order_items),
          (SELECT count(*) FROM raw.order_payments),
          (SELECT sum((data->>'price')::numeric) FROM raw.order_items),
          (SELECT sum((data->>'payment_value')::numeric) FROM raw.order_payments),
          (SELECT sum((i.data->>'price')::numeric) FROM raw.order_items i JOIN raw.orders o
           ON i.data->>'order_id'=o.data->>'order_id' WHERE o.data->>'order_status'='delivered')""").fetchone()
    overview = results["01_overview"][0]
    assert (
        overview["orders"],
        overview["items"],
        overview["payment_entries"],
        overview["all_status_item_value_brl"],
        overview["payment_value_brl"],
        overview["delivered_item_value_brl"],
    ) == raw
    delivered = overview["delivered_item_value_brl"]
    assert sum(r["delivered_item_value_brl"] for r in results["02_monthly_sales"]) == delivered
    assert sum(r["delivered_item_value_brl"] for r in results["04_buyer_states"]) == delivered
    assert (
        sum(r["payment_value_brl"] for r in results["05_payment_mix"])
        == overview["payment_value_brl"]
    )
    repeat = results["06_repeat_buyers"][0]
    assert repeat["delivered_orders"] == sum(
        r["delivered_orders"] for r in results["02_monthly_sales"]
    )
    assert repeat["repeat_buyers"] <= repeat["delivered_buyers"] <= repeat["delivered_orders"]
    fx = results["08_fx_coverage"][0]
    assert (
        fx["covered_item_value_brl"] + fx["uncovered_item_value_brl"]
        == overview["all_status_item_value_brl"]
    )
    assert fx["total_orders"] == overview["orders"] and 0 < fx["covered_days"] < fx["calendar_days"]
    assert len(results["03_top_categories"]) == len(results["07_top_sellers"]) == 10
    return results, hashes, status[0]


def cell(value):
    if value is None:
        return "—"
    if isinstance(value, Decimal):
        return format(value, ",.2f") if value.as_tuple().exponent < 0 else format(value, ",.0f")
    return str(value).replace("|", "\\|").replace("\n", " ")


def main():
    results, hashes, publication_id = execute_queries(load_settings())
    generated = datetime.now(UTC).isoformat()
    report = {
        "generated_at": generated,
        "publication_run_id": publication_id,
        "source_attribution": "Brazilian E-Commerce Public Dataset by Olist (Kaggle)",
        "derived_data_license": "CC BY-NC-SA 4.0",
        "queries": results,
    }
    (ROOT / "docs/analytics-results.json").write_text(
        json.dumps(report, indent=2, default=str) + "\n"
    )
    lines = [
        "# E-commerce analytics — verified snapshot",
        "",
        "[Findings and interpretation](analytics.md) · [Documentation](README.md)",
        "",
        f"Generated {generated}; publication `{publication_id}`.",
        "",
        "Historical Olist snapshot, not a current trading dashboard. All financial values are BRL unless named USD. Revenue proxy = delivered-order item prices, excluding freight, refunds and fees. Payments are independent tender amounts. SQL runs in one read-only repeatable-read transaction.",
        "",
        "Derived aggregate results: attribution to [Olist on Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Changes: typed joins, status filters, grouping and calculations. No endorsement implied.",
        "",
        "The first/last months are partial snapshot periods. Category/seller order counts are not additive across groups. Repeat-buyer share is snapshot-wide, not cohort retention or customer lifetime value. USD totals are partial coverage only.",
        "",
    ]
    for name, question in QUESTIONS:
        rows = results[name]
        lines += ["## " + question, "", f"[Reproduce this SQL](../sql/analytics/{name}.sql)", ""]
        columns = list(rows[0])
        lines += [
            "| " + " | ".join(columns) + " |",
            "| " + " | ".join("---" for _ in columns) + " |",
        ]
        lines += ["| " + " | ".join(cell(row[c]) for c in columns) + " |" for row in rows]
        lines += [""]
    (ROOT / "docs/analytics-results.md").write_text("\n".join(lines))
    evidence = {
        "status": "PASS",
        "verified_at": generated,
        "publication_run_id": publication_id,
        "read_only_repeatable_read": True,
        "query_count": len(results),
        "query_sha256": hashes,
        "result_row_counts": {k: len(v) for k, v in results.items()},
        "validation": {
            "raw_overview_totals": "PASS",
            "monthly_and_state_revenue": "PASS",
            "payment_mix_total": "PASS",
            "repeat_order_counts": "PASS",
            "fx_coverage_partition": "PASS",
        },
        "artifacts": ["docs/analytics-results.md", "docs/analytics-results.json"],
    }
    (ROOT / "docs/phase9-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print("Phase 9 analytics verification PASS; eight queries and aggregate report written")


if __name__ == "__main__":
    main()
