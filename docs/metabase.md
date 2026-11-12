# Metabase dashboard

Metabase runs as a separate Docker service at http://localhost:3000. Airflow
refreshes its data by publishing validated warehouse tables; Metabase queries
those tables when you open or refresh a dashboard. No Metabase task is needed
in the DAG.

## Start

After the [PostgreSQL/source setup](setup.md):

```bash
bash scripts/metabase.sh setup
bash scripts/metabase.sh status
```

Setup creates missing secrets in ignored `.env`, provisions `metabase_app` as a
separate PostgreSQL application database, grants `metabase_reporting` read-only
access to existing and future `published` tables, and starts the pinned Metabase
container. It also creates a local administrator, the read-only warehouse
connection, and an eight-question **E-commerce overview** dashboard. It preserves existing databases, dashboards and passwords on rerun.
Dashboards and accounts persist in the existing PostgreSQL named volume.

```bash
bash scripts/metabase.sh start
bash scripts/metabase.sh logs
bash scripts/metabase.sh stop
```

The application database stores Metabase users, saved questions and dashboards;
it is distinct from the warehouse connection configured below. Keep `.env` with
your volumes. Back up `metabase_app` separately from the warehouse, retain
`METABASE_ENCRYPTION_SECRET_KEY`, and back up before upgrading the image.

## Open the dashboard

Open http://localhost:3000 and sign in using `METABASE_ADMIN_EMAIL` and
`METABASE_ADMIN_PASSWORD` in ignored `.env`. The setup command prints the dashboard
URL, including `#refresh=300` for a five-minute refresh interval while viewing it.
No initial wizard or manual query creation is required.

Setup connects to `postgres:5432` inside Docker, using `POSTGRES_DB` and the
`metabase_reporting` login with `METABASE_REPORTING_PASSWORD`. Schema sync includes
only `published`. The application database uses its own `metabase_app` login.
If tables have not been published yet, run `python -m src.quality.publication`
or the [Airflow pipeline](airflow.md), then sync the warehouse schema in Metabase. The dashboard questions query the current
publication when opened/refreshed.

Repeated setup preserves an existing populated dashboard and existing passwords.
If you change the Metabase administrator password in the UI, update its `.env`
entry before running setup again. An existing installation initialized manually
must supply its administrator email/password in `.env` for provisioning.

To apply the spacious layout and shorter titles to an existing starter dashboard:

```bash
.venv/bin/python -m scripts.setup_metabase --update-layout
```

This updates saved chart names and panel sizes while retaining their SQL and filters.
Normal setup continues to preserve dashboard customizations.

## Dashboard questions

Setup saves the eight existing queries from [`sql/analytics`](../sql/analytics)
with short titles in a full-width, single-column layout. Each panel has extra
height for its chart or table. You can edit charts and add filters in Metabase.

| SQL file | Suggested visualization |
|---|---|
| `01_overview.sql` | Table of headline counts and BRL totals |
| `02_monthly_sales.sql` | Line: purchase month vs delivered item value |
| `03_top_categories.sql` | Bar: category vs delivered item value |
| `04_buyer_states.sql` | Bar: buyer state vs delivered item value |
| `05_payment_mix.sql` | Bar: payment type vs payment value |
| `06_repeat_buyers.sql` | Table of buyers and repeat-buyer share |
| `07_top_sellers.sql` | Bar: seller rank vs delivered item value |
| `08_fx_coverage.sql` | Table of covered/uncovered amounts and days |

These SQL questions use `published` tables and avoid multiplying items by payment rows.
The dashboard and questions include this description:

> Historical Olist snapshot (2016–2018). Delivered item value is a sales proxy,
> excluding freight, refunds and fees. Payments are tender amounts. USD values
> have partial FX coverage. Source: Brazilian E-Commerce Public Dataset by Olist
> (Kaggle), CC BY-NC-SA 4.0; adapted through typed joins and aggregation.

The checked-in [analytics report](analytics-results.md) remains a reproducible
snapshot/reference. It is not the live dashboard.

## Refresh behavior

Set dashboard auto-refresh to **5 minutes** while viewing it. Reopening or manually
refreshing also runs its questions again, subject to any query caching settings.
Schema sync discovers tables/columns; it does not refresh warehouse data.

Airflow runs `publish` after successful ingestion/operational checks and then
`analytics`. If publication fails, the dashboard retains the previous validated
data. If analytics fails after publication, the dashboard can already see the new
publication; inspect the failed analytics task. This historical dataset changes
only when ingested source state changes, so a successful replay can leave charts
unchanged.

The service binds to localhost. Public hosting and authentication/TLS deployment
are outside this local setup.

Official references: [Docker deployment](https://www.metabase.com/docs/latest/installation-and-operation/running-metabase-on-docker),
[application database](https://www.metabase.com/docs/latest/installation-and-operation/configuring-application-database),
[dashboard auto-refresh](https://www.metabase.com/docs/latest/dashboards/introduction#auto-refresh).

## Portfolio screenshot

The README uses [an actual dashboard capture](screenshots/metabase-dashboard.png)
showing the monthly-sales and category panels. It is a static image, not an
embedded live dashboard. The first/last months are partial snapshot periods.

To recapture after starting and provisioning Metabase, use the optional
`scripts.capture_metabase` helper. It requires `websocket-client==1.9.0` in the
activated environment and a temporary Chromium CDP endpoint; neither is needed
for the pipeline or CI.

```bash
docker run -d --rm --name portfolio-capture \
  --network ecommerce-data-platform_default -p 127.0.0.1:9222:9222 \
  chromedp/headless-shell:stable
python -m scripts.capture_metabase
docker stop portfolio-capture
```

The helper reads credentials from ignored `.env`, captures the real rendered
panels, and closes its browser tab and temporary Metabase session. It preserves
saved dashboard layout and SQL. The browser image is optional capture tooling,
not a pinned pipeline dependency. Visually review the image after recapturing.
