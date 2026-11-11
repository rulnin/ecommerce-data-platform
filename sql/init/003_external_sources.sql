CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS metadata;
CREATE TABLE IF NOT EXISTS metadata.external_runs (
 run_id uuid PRIMARY KEY, source text NOT NULL, batch_id text NOT NULL,
 status text NOT NULL CHECK (status IN ('running','success','failed')),
 started_at timestamptz NOT NULL DEFAULT clock_timestamp(), finished_at timestamptz,
 counts jsonb NOT NULL DEFAULT '{}', provenance jsonb NOT NULL DEFAULT '{}', error_code text
);
CREATE TABLE IF NOT EXISTS metadata.external_checkpoints (
 source text PRIMARY KEY, watermark bigint NOT NULL, run_id uuid NOT NULL REFERENCES metadata.external_runs,
 updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS raw.fx_rates (
 base_currency text NOT NULL CHECK (base_currency='USD'),
 quote_currency text NOT NULL CHECK (quote_currency='BRL'),
 rate_date date NOT NULL, provider text NOT NULL CHECK (provider='ECB'),
 rate numeric(38,12) NOT NULL CHECK (rate > 0),
 run_id uuid NOT NULL REFERENCES metadata.external_runs,
 PRIMARY KEY (base_currency,quote_currency,rate_date)
);
CREATE TABLE IF NOT EXISTS raw.fx_requests (
 requested_date date PRIMARY KEY, rate_date date NOT NULL,
 CHECK (rate_date <= requested_date),
 run_id uuid NOT NULL REFERENCES metadata.external_runs
);
CREATE TABLE IF NOT EXISTS raw.inventory (
 product_id text PRIMARY KEY, quantity integer NOT NULL CHECK (quantity >= 0),
 is_deleted boolean NOT NULL, updated_at timestamptz NOT NULL,
 change_seq bigint NOT NULL CHECK (change_seq > 0),
 is_synthetic boolean NOT NULL DEFAULT true CHECK (is_synthetic),
 run_id uuid NOT NULL REFERENCES metadata.external_runs
);
CREATE TABLE IF NOT EXISTS raw.stock_movements (
 movement_id bigint PRIMARY KEY, product_id text NOT NULL, delta integer NOT NULL,
 is_deleted boolean NOT NULL, updated_at timestamptz NOT NULL,
 change_seq bigint NOT NULL CHECK (change_seq > 0),
 is_synthetic boolean NOT NULL DEFAULT true CHECK (is_synthetic),
 run_id uuid NOT NULL REFERENCES metadata.external_runs
);
