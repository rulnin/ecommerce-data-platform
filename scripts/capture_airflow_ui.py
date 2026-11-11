"""Capture the real localhost Airflow UI via an ephemeral Chromium CDP endpoint."""

import base64
import importlib
import json
import time
from contextlib import closing
from pathlib import Path

import requests
from dotenv import dotenv_values


def capture(name, path="/dags/ecommerce_pipeline"):
    websocket = importlib.import_module("websocket")
    tab = requests.put("http://127.0.0.1:9222/json/new?about:blank", timeout=10).json()
    config = dotenv_values(".env")
    sequence = 0
    with closing(
        websocket.create_connection(tab["webSocketDebuggerUrl"], timeout=20, suppress_origin=True)
    ) as socket:

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
            return (
                call("Runtime.evaluate", {"expression": expression, "returnByValue": True})
                .get("result", {})
                .get("value")
            )

        call("Page.enable")
        call(
            "Emulation.setDeviceMetricsOverride",
            {"width": 1440, "height": 1100, "deviceScaleFactor": 1, "mobile": False},
        )
        call("Page.navigate", {"url": "http://airflow-api:8080" + path})
        for _ in range(30):
            time.sleep(1)
            if evaluate("!!document.querySelector('input[type=password]')"):
                username = json.dumps("admin")
                password = json.dumps(config["AIRFLOW_ADMIN_PASSWORD"])
                evaluate(
                    "document.querySelector('input[name=username]').value="
                    + username
                    + ";document.querySelector('input[type=password]').value="
                    + password
                    + ";document.querySelector('input[type=submit],button[type=submit]').click()"
                )
                break
            if evaluate("document.body && document.body.innerText.includes('ecommerce_pipeline')"):
                break
        time.sleep(4)
        call("Page.navigate", {"url": "http://airflow-api:8080" + path})
        for _ in range(30):
            time.sleep(1)
            if evaluate(
                "document.body && document.body.innerText.includes('ecommerce_pipeline') && !document.querySelector('input[type=password]')"
            ):
                break
        else:
            raise RuntimeError("Airflow authenticated DAG page did not load")
        time.sleep(3)
        result = call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True})
        output = Path("docs/screenshots") / (name + ".png")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(base64.b64decode(result["data"]))
    requests.get("http://127.0.0.1:9222/json/close/" + tab["id"], timeout=10)
    return str(output)
