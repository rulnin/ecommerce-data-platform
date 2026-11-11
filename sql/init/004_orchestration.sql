CREATE SCHEMA IF NOT EXISTS metadata;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE TABLE IF NOT EXISTS metadata.orchestration_steps (
 step_id uuid PRIMARY KEY, dag_run_id text NOT NULL, task_id text NOT NULL,
 batch_date date NOT NULL, attempt integer NOT NULL CHECK(attempt>0),
 status text NOT NULL CHECK(status IN ('running','success','failed')),
 started_at timestamptz NOT NULL DEFAULT clock_timestamp(), finished_at timestamptz,
 source_run_id text, error_code text
);
CREATE TABLE IF NOT EXISTS metadata.orchestration_controls (
 dag_run_id text PRIMARY KEY, released boolean NOT NULL DEFAULT false
);
CREATE TABLE IF NOT EXISTS staging.daily_ingestion_summary (
 batch_date date PRIMARY KEY, orders bigint NOT NULL, items bigint NOT NULL,
 payments bigint NOT NULL, item_value numeric NOT NULL, payment_value numeric NOT NULL,
 dag_run_id text NOT NULL, computed_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
