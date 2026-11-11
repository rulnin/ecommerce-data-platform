-- Additive Phase 2 migration. Raw fields remain original strings in JSONB.
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS metadata;
CREATE TABLE IF NOT EXISTS metadata.ingestion_runs (
 run_id uuid PRIMARY KEY, source text NOT NULL, batch_id text NOT NULL,
 mode text NOT NULL CHECK (mode IN ('full','incremental')),
 watermark date, status text NOT NULL CHECK (status IN ('running','success','failed')),
 started_at timestamptz NOT NULL DEFAULT clock_timestamp(), finished_at timestamptz,
 counts jsonb NOT NULL DEFAULT '{}', input_hashes jsonb NOT NULL,
 error_code text
);
CREATE TABLE IF NOT EXISTS metadata.checkpoints (
 source text PRIMARY KEY, batch_id text NOT NULL, watermark date,
 run_id uuid NOT NULL REFERENCES metadata.ingestion_runs, updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS metadata.rejections (
 run_id uuid NOT NULL REFERENCES metadata.ingestion_runs, source text NOT NULL,
 record_number bigint, field text, error_code text NOT NULL,
 reported_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS raw.customers (
 business_key text PRIMARY KEY CHECK (business_key <> ''),
 data jsonb NOT NULL CHECK (jsonb_typeof(data) = 'object'),
 row_hash text NOT NULL CHECK (row_hash ~ '^[0-9a-f]{64}$'),
 CHECK (coalesce(data->>'customer_id','') <> ''),
 first_run_id uuid NOT NULL REFERENCES metadata.ingestion_runs,
 last_run_id uuid NOT NULL REFERENCES metadata.ingestion_runs,
 loaded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS raw.orders (
 business_key text PRIMARY KEY CHECK (business_key <> ''),
 data jsonb NOT NULL CHECK (jsonb_typeof(data) = 'object'),
 row_hash text NOT NULL CHECK (row_hash ~ '^[0-9a-f]{64}$'),
 CHECK (coalesce(data->>'order_id','') <> ''),
 first_run_id uuid NOT NULL REFERENCES metadata.ingestion_runs,
 last_run_id uuid NOT NULL REFERENCES metadata.ingestion_runs,
 loaded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS raw.order_items (
 business_key text PRIMARY KEY CHECK (business_key <> ''),
 data jsonb NOT NULL CHECK (jsonb_typeof(data) = 'object'),
 row_hash text NOT NULL CHECK (row_hash ~ '^[0-9a-f]{64}$'),
 CHECK (coalesce(data->>'order_id','') <> ''),
 CHECK (coalesce(data->>'order_item_id','') <> ''),
 first_run_id uuid NOT NULL REFERENCES metadata.ingestion_runs,
 last_run_id uuid NOT NULL REFERENCES metadata.ingestion_runs,
 loaded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS raw.order_payments (
 business_key text PRIMARY KEY CHECK (business_key <> ''),
 data jsonb NOT NULL CHECK (jsonb_typeof(data) = 'object'),
 row_hash text NOT NULL CHECK (row_hash ~ '^[0-9a-f]{64}$'),
 CHECK (coalesce(data->>'order_id','') <> ''),
 CHECK (coalesce(data->>'payment_sequential','') <> ''),
 first_run_id uuid NOT NULL REFERENCES metadata.ingestion_runs,
 last_run_id uuid NOT NULL REFERENCES metadata.ingestion_runs,
 loaded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS raw.order_reviews (
 business_key text PRIMARY KEY CHECK (business_key <> ''),
 data jsonb NOT NULL CHECK (jsonb_typeof(data) = 'object'),
 row_hash text NOT NULL CHECK (row_hash ~ '^[0-9a-f]{64}$'),
 first_run_id uuid NOT NULL REFERENCES metadata.ingestion_runs,
 last_run_id uuid NOT NULL REFERENCES metadata.ingestion_runs,
 loaded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS raw.products (
 business_key text PRIMARY KEY CHECK (business_key <> ''),
 data jsonb NOT NULL CHECK (jsonb_typeof(data) = 'object'),
 row_hash text NOT NULL CHECK (row_hash ~ '^[0-9a-f]{64}$'),
 CHECK (coalesce(data->>'product_id','') <> ''),
 first_run_id uuid NOT NULL REFERENCES metadata.ingestion_runs,
 last_run_id uuid NOT NULL REFERENCES metadata.ingestion_runs,
 loaded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS raw.sellers (
 business_key text PRIMARY KEY CHECK (business_key <> ''),
 data jsonb NOT NULL CHECK (jsonb_typeof(data) = 'object'),
 row_hash text NOT NULL CHECK (row_hash ~ '^[0-9a-f]{64}$'),
 CHECK (coalesce(data->>'seller_id','') <> ''),
 first_run_id uuid NOT NULL REFERENCES metadata.ingestion_runs,
 last_run_id uuid NOT NULL REFERENCES metadata.ingestion_runs,
 loaded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS raw.category_translation (
 business_key text PRIMARY KEY CHECK (business_key <> ''),
 data jsonb NOT NULL CHECK (jsonb_typeof(data) = 'object'),
 row_hash text NOT NULL CHECK (row_hash ~ '^[0-9a-f]{64}$'),
 CHECK (coalesce(data->>'product_category_name','') <> ''),
 first_run_id uuid NOT NULL REFERENCES metadata.ingestion_runs,
 last_run_id uuid NOT NULL REFERENCES metadata.ingestion_runs,
 loaded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS raw.geolocation (
 business_key text PRIMARY KEY CHECK (business_key <> ''),
 data jsonb NOT NULL CHECK (jsonb_typeof(data) = 'object'),
 row_hash text NOT NULL CHECK (row_hash ~ '^[0-9a-f]{64}$'),
 first_run_id uuid NOT NULL REFERENCES metadata.ingestion_runs,
 last_run_id uuid NOT NULL REFERENCES metadata.ingestion_runs,
 loaded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
