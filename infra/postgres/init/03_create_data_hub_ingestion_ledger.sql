\connect quant_data_hub

CREATE TABLE IF NOT EXISTS ingestion_runs (
    id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(128) NOT NULL UNIQUE,
    task_type VARCHAR(64) NOT NULL,
    source_name VARCHAR(128) NOT NULL,
    dataset_code VARCHAR(128) NOT NULL,
    timeframe VARCHAR(16) NOT NULL,
    status VARCHAR(32) NOT NULL,
    storage_target VARCHAR(128) NOT NULL,
    start_date DATE,
    end_date DATE,
    row_count BIGINT NOT NULL DEFAULT 0,
    symbol_count BIGINT NOT NULL DEFAULT 0,
    trading_day_count BIGINT NOT NULL DEFAULT 0,
    duplicate_key_rows BIGINT NOT NULL DEFAULT 0,
    input_params JSONB,
    output_summary JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_ingestion_runs_source_dataset_created
    ON ingestion_runs (source_name, dataset_code, created_at);

CREATE INDEX IF NOT EXISTS ix_ingestion_runs_status_created
    ON ingestion_runs (status, created_at);

CREATE INDEX IF NOT EXISTS ix_ingestion_runs_timeframe_range
    ON ingestion_runs (timeframe, start_date, end_date);

CREATE TABLE IF NOT EXISTS ingestion_quality_checks (
    id BIGSERIAL PRIMARY KEY,
    check_id VARCHAR(128) NOT NULL UNIQUE,
    run_id VARCHAR(128) NOT NULL,
    check_name VARCHAR(128) NOT NULL,
    check_status VARCHAR(32) NOT NULL,
    expected_condition TEXT NOT NULL,
    observed_value TEXT,
    details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_ingestion_quality_checks_run_id
    ON ingestion_quality_checks (run_id);

CREATE INDEX IF NOT EXISTS ix_ingestion_quality_checks_status_created
    ON ingestion_quality_checks (check_status, created_at);

CREATE TABLE IF NOT EXISTS ingestion_artifacts (
    id BIGSERIAL PRIMARY KEY,
    artifact_id VARCHAR(128) NOT NULL UNIQUE,
    run_id VARCHAR(128) NOT NULL,
    artifact_type VARCHAR(64) NOT NULL,
    storage_type VARCHAR(32) NOT NULL,
    bucket_name VARCHAR(128),
    object_key TEXT,
    uri TEXT,
    content_type VARCHAR(128),
    file_size_bytes BIGINT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_ingestion_artifacts_run_id
    ON ingestion_artifacts (run_id);

CREATE INDEX IF NOT EXISTS ix_ingestion_artifacts_type_created
    ON ingestion_artifacts (artifact_type, created_at);
