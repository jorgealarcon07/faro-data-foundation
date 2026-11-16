CREATE SCHEMA IF NOT EXISTS faro;
CREATE TABLE IF NOT EXISTS faro.sources (
 dataset_sha256 text PRIMARY KEY, parquet_sha256 text NOT NULL,
 namespace text NOT NULL, data_kind text NOT NULL CHECK(data_kind IN ('synthetic','public_real_historical')),
 expected_rows bigint NOT NULL, metadata jsonb NOT NULL, loaded_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS faro.source_rows (
 dataset_sha256 text NOT NULL REFERENCES faro.sources(dataset_sha256),
 source_row_id text NOT NULL, sheet text NOT NULL, row_number int NOT NULL,
 invoice text, stock_code text, description text, quantity_text text, event_text text,
 price_text text, customer_text text, country text,
 quantity numeric, unit_price numeric, event_local_time timestamp,
 PRIMARY KEY (dataset_sha256, source_row_id)
);
CREATE INDEX IF NOT EXISTS source_rows_date ON faro.source_rows(dataset_sha256,event_local_time);
CREATE TABLE IF NOT EXISTS faro.runs (
 run_id text PRIMARY KEY, namespace text NOT NULL, dataset_sha256 text NOT NULL,
 candidate_schema text NOT NULL UNIQUE, state text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz,
 start_date date, end_date date, previous_run text, source_metadata jsonb NOT NULL,
 manifest jsonb, error_code text
);
CREATE TABLE IF NOT EXISTS faro.publications (
 namespace text PRIMARY KEY, run_id text NOT NULL REFERENCES faro.runs(run_id),
 candidate_schema text NOT NULL, published_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS faro.events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, run_id text NOT NULL,
 occurred_at timestamptz NOT NULL DEFAULT now(), stage text NOT NULL, payload jsonb NOT NULL
);
REVOKE ALL ON SCHEMA faro FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA faro FROM PUBLIC;

