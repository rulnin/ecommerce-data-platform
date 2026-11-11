# FX source contract — Phase 3

Selected API: Frankfurter v2, fixed European Central Bank provider:
`GET https://api.frankfurter.dev/v2/providers/ecb/rate/USD/BRL?date=YYYY-MM-DD`.
No API key or paid subscription is required. The v2 provider-specific route avoids
the default multi-provider blend. These are reference rates, not executable trading
quotes. See [Frankfurter documentation](https://frankfurter.dev/) and the
[ECB rate publication page](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html).
Direct provider rates remain subject to the provider's terms linked in API metadata.

## Response and rate direction

Actual response for requested 2017-11-25:

```json
{"date":"2017-11-24","base":"USD","quote":"BRL","rate":3.2314}
```

`date` is the observation date, not necessarily the requested calendar date. `rate`
means BRL per 1 USD: USD amount multiplied by rate gives BRL; BRL amount divided by
rate gives USD. Future marts must use the transaction's historical rate or an
explicit approved fallback, never the latest rate for historical sales.
The parser uses Decimal and rejects nonpositive/non-finite rates, wrong currencies,
malformed dates, excessive precision/range, future observations relative to the
requested date and observations older than seven calendar days. This seven-day
policy is a project freshness guard, not an API guarantee.

## Historical coverage evidence

docs/fx-api-probes.json captures the endpoint, provider metadata and live probes
performed 2026-11-10:

| Requested date | HTTP | Returned rate date | USD/BRL |
|---|---:|---|---:|
| 2016-09-04 | 200 | 2016-09-02 | 3.2653 |
| 2017-11-24 | 200 | 2017-11-24 | 3.2314 |
| 2017-11-25 | 200 | 2017-11-24 | 3.2314 |
| 2018-10-17 | 200 | 2018-10-17 | 3.7372 |
| 1999-01-04 | 404 | — | — |
| 1998-12-31 | 404 | — | — |

The provider metadata starts in 1999, but that is not proof this pair exists from
that date: the actual 1999 USD/BRL probe returned 404. Olist-era boundaries and a
weekend are verified; every calendar day in the whole history has not been fetched.
Unavailable history fails rather than substituting today's value. Weekends/holidays
can return an earlier business-day observation. The returned rate date is always
retained separately from requested date.

## Loading and caching

```bash
source .venv/bin/activate
python -m src.ingestion.api_ingestion --date 2017-11-25 --batch-id fx-2017-11-25
# Explicitly recheck the provider for a possible corrected observation:
python -m src.ingestion.api_ingestion --date 2017-11-25 --batch-id fx-refresh --refresh
```

raw.fx_rates has one row per base/quote/actual rate date, restricted to USD/BRL
and ECB. Rate is numeric(38,12), strictly positive. raw.fx_requests maps requested
dates to returned observation dates. A cache hit avoids the network; --refresh
upserts corrected rate values without duplicate observations. USD/BRL identity is
fixed by database constraints. Requested-date mappings may change on refresh.

The client uses at most three attempts, connect/read timeouts of 10/30 seconds,
bounded 1/2-second backoff and a 64 KiB response limit. 429 and server/network errors
retry; other non-200 statuses fail without retries. Status/schema/transport errors
are sanitized, with no response payloads logged. Success/failure attempts are stored
in metadata.external_runs with source fx_ecb, dates, endpoint, counts and provider.
Data and success status commit together. Tests use deterministic in-code fixtures;
live network calls are not required for default tests.
