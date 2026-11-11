"""Optional static portfolio capture; no DB credentials or application server.

Requires a temporary localhost CDP browser and optional websocket-client 1.9.0.
See docs/analytics.md. Normal query generation and CI need neither dependency.
"""

import base64
import hashlib
import html
import importlib
import json
import re
from contextlib import closing
from decimal import Decimal

import requests

from scripts.dbt import ROOT


def scorecard(results):
    q = results["queries"]
    overview = q["01_overview"][0]
    fx, repeat = q["08_fx_coverage"][0], q["06_repeat_buyers"][0]

    def money(value):
        return f"{Decimal(value):,.2f}"

    def table(rows, columns):
        header = "".join("<th>" + html.escape(label) + "</th>" for _, label in columns)
        body = "".join(
            "<tr>"
            + "".join(
                "<td>"
                + html.escape(
                    (money(row[key]) if key.endswith("_brl") else str(row[key]).replace("_", " "))
                )
                + "</td>"
                for key, _ in columns
            )
            + "</tr>"
            for row in rows
        )
        return "<table><thead><tr>" + header + "</tr></thead><tbody>" + body + "</tbody></table>"

    categories = table(
        q["03_top_categories"][:5],
        [("category", "Category"), ("delivered_item_value_brl", "BRL"), ("share_pct", "Share %")],
    )
    payments = table(
        q["05_payment_mix"],
        [
            ("payment_type", "Payment type"),
            ("payment_value_brl", "BRL"),
            ("value_share_pct", "Share %"),
        ],
    )
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
    *{{box-sizing:border-box}}body{{margin:0;background:#eef2f7;color:#14243a;font:18px Arial,sans-serif}}
    main{{max-width:1360px;margin:30px auto;background:white;padding:42px;border-top:8px solid #167c80}}
    .eyebrow{{font-size:15px;letter-spacing:2px;color:#167c80;font-weight:bold}}h1{{font-size:42px;margin:12px 0}}
    .sub{{color:#516174;line-height:1.5}}.cards,.split{{display:grid;gap:22px;margin:28px 0}}.cards{{grid-template-columns:repeat(3,1fr)}}
    .split{{grid-template-columns:1fr 1fr}}.card{{background:#eff7f7;border:1px solid #d5e6e6;padding:22px}}
    .value{{font-size:33px;font-weight:bold;margin:12px 0}}.label{{font-size:15px;color:#516174}}h2{{font-size:22px}}
    table{{border-collapse:collapse;width:100%;font-size:16px}}th,td{{text-align:left;padding:12px 8px;border-bottom:1px solid #dce3eb}}th{{color:#516174;font-size:14px}}
    .notice{{background:#fff6df;border-left:5px solid #c98c21;padding:18px;line-height:1.6}}
    footer{{font-size:13px;line-height:1.6;color:#516174;margin-top:26px}}
    </style></head><body><main><div class="eyebrow">VERIFIED SQL RESULTS · HISTORICAL OLIST SNAPSHOT</div>
    <h1>E-commerce, without double counting</h1>
    <div class="sub">{overview["first_purchase_date"]} — {overview["last_purchase_date"]} · Read-only queries against quality-gated published tables</div>
    <div class="cards"><div class="card"><div class="label">ORDERS · ALL STATUSES</div><div class="value">{int(overview["orders"]):,}</div><div class="label">{int(overview["items"]):,} items / {int(overview["payment_entries"]):,} payment entries</div></div>
    <div class="card"><div class="label">DELIVERED ITEM VALUE · BRL</div><div class="value">{money(overview["delivered_item_value_brl"])}</div><div class="label">Sales proxy; excludes freight, refunds and fees</div></div>
    <div class="card"><div class="label">PAYMENT VALUE · BRL</div><div class="value">{money(overview["payment_value_brl"])}</div><div class="label">Tender amount; separate from delivered item value</div></div></div>
    <div class="split"><section><h2>Top categories · delivered item value</h2>{categories}</section><section><h2>Payment mix · all statuses</h2>{payments}</section></div>
    <div class="notice"><b>Coverage is part of the result.</b> Historical FX covers {fx["covered_days"]} / {fx["calendar_days"]} calendar days and {fx["order_coverage_pct"]}% of orders. USD totals are partial.<br>
    Repeat delivered buyers: {repeat["repeat_buyer_pct"]}% of people in this snapshot — not cohort retention.</div>
    <footer>Source: Brazilian E-Commerce Public Dataset by Olist (Kaggle) · Derived aggregates: CC BY-NC-SA 4.0. Changes: status filters, grouping and calculations.<br>
    No Olist endorsement. Synthetic inventory is excluded from these sales metrics. Generated {html.escape(results["generated_at"])}.<br>
    Full results and reproducible SQL: docs/analytics-results.md · Publication {html.escape(results["publication_run_id"])}</footer>
    </main></body></html>"""


def main():
    websocket = importlib.import_module("websocket")
    tab = requests.put("http://127.0.0.1:9222/json/new?about:blank", timeout=10).json()
    records = []
    with closing(
        websocket.create_connection(tab["webSocketDebuggerUrl"], timeout=60, suppress_origin=True)
    ) as socket:
        sequence = 0

        def call(method, params=None):
            nonlocal sequence
            sequence += 1
            socket.send(json.dumps({"id": sequence, "method": method, "params": params or {}}))
            while True:
                result = json.loads(socket.recv())
                if result.get("id") == sequence:
                    if "error" in result:
                        raise RuntimeError("CDP command failed")
                    return result.get("result", {})

        def evaluate(expression):
            result = call(
                "Runtime.evaluate",
                {"expression": expression, "awaitPromise": True, "returnByValue": True},
            )
            if result.get("exceptionDetails"):
                raise RuntimeError(str(result["exceptionDetails"]))
            return result.get("result", {}).get("value")

        call("Page.enable")
        call(
            "Emulation.setDeviceMetricsOverride",
            {"width": 1440, "height": 1100, "deviceScaleFactor": 1, "mobile": False},
        )
        evaluate(
            "(async()=>{window.mermaid=(await import('https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.esm.min.mjs')).default;mermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:'neutral',fontFamily:'Arial',flowchart:{htmlLabels:false,useMaxWidth:false}});return true})()"
        )
        diagrams = ROOT / "docs/diagrams"
        diagrams.mkdir(parents=True, exist_ok=True)
        for path in (
            ROOT / "README.md",
            ROOT / "docs/architecture.md",
            ROOT / "docs/data-model.md",
        ):
            for i, definition in enumerate(
                re.findall(r"```mermaid\n(.*?)```", path.read_text(), re.S)
            ):
                result = evaluate(
                    "(async()=>{let text="
                    + json.dumps(definition)
                    + ";let parsed=await mermaid.parse(text);let rendered=await mermaid.render("
                    + json.dumps(path.stem.replace("-", "_") + "_" + str(i))
                    + ",text);return {type:parsed.diagramType,svg:rendered.svg}})()"
                )
                target = diagrams / (path.stem.lower() + "-" + str(i + 1) + ".svg")
                target.write_text(result["svg"])
                records.append(
                    {
                        "source": str(path.relative_to(ROOT)),
                        "diagram": i + 1,
                        "type": result["type"],
                        "sha256": hashlib.sha256(definition.encode()).hexdigest(),
                        "svg": str(target.relative_to(ROOT)),
                        "status": "PASS",
                    }
                )
        report = json.loads((ROOT / "docs/analytics-results.json").read_text())
        frame = call("Page.getFrameTree")["frameTree"]["frame"]["id"]
        call("Page.setDocumentContent", {"frameId": frame, "html": scorecard(report)})
        expected_value = (
            f"{Decimal(report['queries']['01_overview'][0]['delivered_item_value_brl']):,.2f}"
        )
        assert evaluate("document.body.innerText.includes(" + json.dumps(expected_value) + ")")
        screenshot = call(
            "Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True}
        )
        (ROOT / "docs/screenshots/phase9-analytics.png").write_bytes(
            base64.b64decode(screenshot["data"])
        )
    requests.get("http://127.0.0.1:9222/json/close/" + tab["id"], timeout=10)
    (ROOT / "docs/phase9-render-evidence.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "mermaid_version": "11.4.1",
                "diagrams": records,
                "screenshot": "docs/screenshots/phase9-analytics.png",
            },
            indent=2,
        )
        + "\n"
    )
    print("Mermaid parse/render and SQL scorecard capture: PASS")


if __name__ == "__main__":
    main()
