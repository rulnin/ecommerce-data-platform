"""Dated ECB USD/BRL reference rates via Frankfurter v2."""

import argparse
import json
import time
from datetime import date
from decimal import Decimal, InvalidOperation

import requests

from src.common.config import load_settings
from src.common.external_audit import audited_run

ENDPOINT = "https://api.frankfurter.dev/v2/providers/ecb/rate/USD/BRL"


class FxError(ValueError):
    """Sanitized transport or source-contract failure."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def parse_rate(body, requested):
    try:
        day = date.fromisoformat(body["date"])
        rate = Decimal(str(body["rate"]))
        if body["base"] != "USD" or body["quote"] != "BRL":
            raise ValueError
        if not rate.is_finite() or rate <= 0 or not 0 <= (requested - day).days <= 7:
            raise ValueError
        if rate.as_tuple().exponent < -12 or rate >= Decimal("1e26"):
            raise ValueError
    except KeyError, TypeError, ValueError, InvalidOperation:
        raise FxError("invalid_rate_contract") from None
    return day, rate


def fetch_rate(requested, session=None, sleep=time.sleep):
    if session is None:
        with requests.Session() as owned:
            return fetch_rate(requested, owned, sleep)
    for attempt in range(3):
        try:
            with session.get(
                ENDPOINT, params={"date": requested.isoformat()}, timeout=(10, 30), stream=True
            ) as response:
                if response.status_code == 429 or response.status_code >= 500:
                    raise requests.ConnectionError
                if response.status_code != 200:
                    raise FxError(f"http_{response.status_code}")
                chunks, size = [], 0
                for chunk in response.iter_content(8192):
                    size += len(chunk)
                    if size > 65536:
                        raise FxError("oversized_response")
                    chunks.append(chunk)
                try:
                    body = json.loads(b"".join(chunks), parse_float=Decimal)
                except ValueError, UnicodeError:
                    raise FxError("invalid_json") from None
                return parse_rate(body, requested)
        except requests.RequestException:
            if attempt == 2:
                raise FxError("transport_retry_exhausted") from None
            sleep(2**attempt)
    raise FxError("transport_retry_exhausted")


def ingest(settings, requested, batch_id, refresh=False, session=None):
    with audited_run(settings, "fx_ecb", batch_id) as (db, run_id, result):
        result["provenance"] = {
            "endpoint": ENDPOINT,
            "provider": "ECB",
            "requested_date": str(requested),
        }
        cached = db.execute(
            """SELECT r.rate_date,r.rate FROM raw.fx_requests q JOIN raw.fx_rates r
            ON r.rate_date=q.rate_date WHERE q.requested_date=%s""",
            (requested,),
        ).fetchone()
        day, rate = cached if cached and not refresh else fetch_rate(requested, session)
        prior = db.execute("SELECT rate FROM raw.fx_rates WHERE rate_date=%s", (day,)).fetchone()
        db.execute(
            """INSERT INTO raw.fx_rates VALUES('USD','BRL',%s,'ECB',%s,%s)
            ON CONFLICT(base_currency,quote_currency,rate_date) DO UPDATE
            SET rate=excluded.rate,run_id=excluded.run_id WHERE fx_rates.rate <> excluded.rate""",
            (day, rate, run_id),
        )
        db.execute(
            """INSERT INTO raw.fx_requests VALUES(%s,%s,%s) ON CONFLICT(requested_date)
            DO UPDATE SET rate_date=excluded.rate_date,run_id=excluded.run_id""",
            (requested, day, run_id),
        )
        result["counts"] = {
            "inserted": int(prior is None),
            "updated": int(prior is not None and prior[0] != rate),
            "cache_hit": bool(cached and not refresh),
        }
        result["provenance"].update(rate_date=str(day), rate=str(rate))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True, type=date.fromisoformat)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    print(json.dumps(ingest(load_settings(), args.date, args.batch_id, args.refresh), indent=2))


if __name__ == "__main__":
    main()
