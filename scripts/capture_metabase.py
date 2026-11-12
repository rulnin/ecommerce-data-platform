"""Capture the actual local dashboard using an optional localhost CDP browser.

Requires websocket-client; see docs/metabase.md. Credentials remain in memory.
"""

import base64
import importlib
import json
import time
from contextlib import closing
from pathlib import Path

import requests
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def main():
    websocket = importlib.import_module("websocket")
    config = dotenv_values(ROOT / ".env")
    base = "http://127.0.0.1:" + config.get("METABASE_PORT", "3000")
    session = requests.Session()
    login = session.post(
        base + "/api/session",
        json={
            "username": config["METABASE_ADMIN_EMAIL"],
            "password": config["METABASE_ADMIN_PASSWORD"],
        },
        timeout=30,
    )
    if not login.ok:
        raise RuntimeError(f"Metabase login failed (HTTP {login.status_code})")
    token = login.json()["id"]
    session.headers["X-Metabase-Session"] = token
    tab = None
    try:
        dashboards = session.get(base + "/api/dashboard", timeout=30)
        dashboards.raise_for_status()
        dashboard = next(d for d in dashboards.json() if d["name"] == "E-commerce overview")
        tab = requests.put("http://127.0.0.1:9222/json/new?about:blank", timeout=10).json()
        with closing(
            websocket.create_connection(
                tab["webSocketDebuggerUrl"], timeout=30, suppress_origin=True
            )
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
                            raise RuntimeError("Browser capture command failed")
                        return result.get("result", {})

            def evaluate(expression):
                result = call("Runtime.evaluate", {"expression": expression, "returnByValue": True})
                if result.get("exceptionDetails"):
                    raise RuntimeError("Dashboard readiness check failed")
                return result.get("result", {}).get("value")

            call("Page.enable")
            call(
                "Emulation.setDeviceMetricsOverride",
                {"width": 1600, "height": 1800, "deviceScaleFactor": 1, "mobile": False},
            )
            call(
                "Network.setCookie",
                {
                    "name": "metabase.SESSION",
                    "value": token,
                    "url": "http://metabase:3000",
                    "httpOnly": True,
                },
            )
            call("Page.navigate", {"url": f"http://metabase:3000/dashboard/{dashboard['id']}"})
            for _ in range(60):
                if evaluate(
                    "document.body && document.body.innerText.includes('Monthly delivered sales')"
                    " && !!document.querySelector('canvas')"
                ):
                    break
                time.sleep(1)
            else:
                raise RuntimeError("Dashboard chart did not finish loading")
            time.sleep(3)
            bounds = evaluate(
                "JSON.stringify(['Monthly delivered sales (BRL)', 'Top product categories (BRL)']"
                ".map(title => Array.from(document.querySelectorAll('*')).find("
                "e => e.children.length === 0 && e.textContent === title))"
                ".map(e => e.closest('.react-grid-item').getBoundingClientRect())"
                ".map(r => ({x:r.x,y:r.y,width:r.width,height:r.height})))"
            )
            panels = json.loads(bounds)
            top = min(r["y"] for r in panels)
            bottom = max(r["y"] + r["height"] for r in panels)
            image = call(
                "Page.captureScreenshot",
                {
                    "format": "png",
                    "captureBeyondViewport": False,
                    "clip": {
                        "x": 0,
                        "y": top - 8,
                        "width": 1580,
                        "height": bottom - top + 16,
                        "scale": 1,
                    },
                },
            )
            (ROOT / "docs/screenshots/metabase-dashboard.png").write_bytes(
                base64.b64decode(image["data"])
            )
    finally:
        if tab:
            requests.get("http://127.0.0.1:9222/json/close/" + tab["id"], timeout=10)
        session.delete(base + "/api/session", timeout=10)
        session.close()
    print("Actual Metabase dashboard captured: docs/screenshots/metabase-dashboard.png")


if __name__ == "__main__":
    main()
