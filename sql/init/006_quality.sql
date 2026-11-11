CREATE SCHEMA IF NOT EXISTS metadata;
CREATE TABLE IF NOT EXISTS metadata.quality_runs (
 run_id uuid PRIMARY KEY,
 started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 finished_at timestamptz,
 status text NOT NULL CHECK (status IN ('running','failed','published')),
 report jsonb NOT NULL DEFAULT '{}'
);
