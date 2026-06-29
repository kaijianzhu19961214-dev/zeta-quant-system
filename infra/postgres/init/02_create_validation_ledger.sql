\connect quant_factor_validation

CREATE TABLE IF NOT EXISTS task_runs (
    id BIGSERIAL PRIMARY KEY,
    task_id VARCHAR(128) NOT NULL UNIQUE,
    task_type VARCHAR(64) NOT NULL,
    task_name VARCHAR(256) NOT NULL,
    owner VARCHAR(128),
    status VARCHAR(32) NOT NULL,
    description TEXT,
    input_params JSONB,
    output_summary JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_task_runs_task_id ON task_runs (task_id);
CREATE INDEX IF NOT EXISTS ix_task_runs_status ON task_runs (status);
CREATE INDEX IF NOT EXISTS ix_task_runs_type_status_created ON task_runs (task_type, status, created_at);
CREATE INDEX IF NOT EXISTS ix_task_runs_owner_created ON task_runs (owner, created_at);

CREATE TABLE IF NOT EXISTS task_artifacts (
    id BIGSERIAL PRIMARY KEY,
    artifact_id VARCHAR(128) NOT NULL UNIQUE,
    task_id VARCHAR(128) NOT NULL,
    artifact_type VARCHAR(64) NOT NULL,
    artifact_name VARCHAR(256),
    storage_type VARCHAR(32) NOT NULL DEFAULT 'minio_s3',
    bucket_name VARCHAR(128) NOT NULL,
    object_key TEXT NOT NULL,
    uri TEXT NOT NULL,
    content_type VARCHAR(128),
    file_size_bytes BIGINT,
    etag VARCHAR(128),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_task_artifacts_task_id ON task_artifacts (task_id);
CREATE INDEX IF NOT EXISTS ix_task_artifacts_type_created ON task_artifacts (artifact_type, created_at);
CREATE INDEX IF NOT EXISTS ix_task_artifacts_bucket_object ON task_artifacts (bucket_name, object_key);
