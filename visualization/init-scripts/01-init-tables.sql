-- Create tables for test results data

-- Create extension for TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Test runs table - stores high-level information about each test run
CREATE TABLE IF NOT EXISTS test_runs (
    id SERIAL PRIMARY KEY,
    test_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    dut_name TEXT NOT NULL,
    result TEXT NOT NULL,
    test_type TEXT NOT NULL,
    start_date TIMESTAMPTZ NOT NULL,
    stop_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Test groups table - stores information about test groups
CREATE TABLE IF NOT EXISTS test_groups (
    id SERIAL PRIMARY KEY,
    test_run_id INTEGER REFERENCES test_runs(id) ON DELETE CASCADE,
    number TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    parent_group_id INTEGER REFERENCES test_groups(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Test cases table - stores information about individual test cases
CREATE TABLE IF NOT EXISTS test_cases (
    id SERIAL PRIMARY KEY,
    test_run_id INTEGER REFERENCES test_runs(id) ON DELETE CASCADE,
    group_id INTEGER REFERENCES test_groups(id) ON DELETE CASCADE,
    number TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    result TEXT NOT NULL,
    status TEXT NOT NULL,
    start_date TIMESTAMPTZ,
    stop_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Metrics table - stores information about test metrics
CREATE TABLE IF NOT EXISTS metrics (
    id SERIAL PRIMARY KEY,
    test_case_id INTEGER REFERENCES test_cases(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    result TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Measurements table - stores information about test measurements
CREATE TABLE IF NOT EXISTS measurements (
    id SERIAL,
    metric_id INTEGER REFERENCES metrics(id) ON DELETE CASCADE,
    test_case_id INTEGER REFERENCES test_cases(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    value JSONB NOT NULL,
    units TEXT NOT NULL,
    dut_name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
);

-- Create hypertable for measurements to enable time-series functionality
SELECT create_hypertable('measurements', 'created_at', if_not_exists => TRUE);

-- Artifacts table - stores metadata about test artifacts stored in MinIO
CREATE TABLE IF NOT EXISTS artifacts (
    id SERIAL,
    test_run_id INTEGER REFERENCES test_runs(id) ON DELETE CASCADE,
    test_case_id INTEGER REFERENCES test_cases(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    original_path TEXT NOT NULL,
    minio_path TEXT NOT NULL,
    content_type TEXT,
    size BIGINT,
    file_hash TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
);

-- Create hypertable for artifacts to enable time-series functionality
SELECT create_hypertable('artifacts', 'created_at', if_not_exists => TRUE);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_test_runs_test_id ON test_runs(test_id);
CREATE INDEX IF NOT EXISTS idx_test_runs_timestamp ON test_runs(timestamp);
CREATE INDEX IF NOT EXISTS idx_test_runs_result ON test_runs(result);
CREATE INDEX IF NOT EXISTS idx_test_cases_result ON test_cases(result);
CREATE INDEX IF NOT EXISTS idx_measurements_name ON measurements(name);
CREATE INDEX IF NOT EXISTS idx_artifacts_name ON artifacts(name);
CREATE INDEX IF NOT EXISTS idx_artifacts_test_run_id ON artifacts(test_run_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_test_case_id ON artifacts(test_case_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_artifacts_file_hash ON artifacts(file_hash, created_at) WHERE file_hash IS NOT NULL;

-- Create a view for test case results with their metrics and measurements
CREATE OR REPLACE VIEW test_case_results AS
SELECT 
    tr.test_id,
    tr.timestamp,
    tr.dut_name,
    tr.result AS test_run_result,
    tr.test_type,
    tr.start_date AS test_run_start_date,
    tr.stop_date AS test_run_stop_date,
    tg.number AS group_number,
    tg.name AS group_name,
    tc.number AS case_number,
    tc.name AS case_name,
    tc.description AS case_description,
    tc.result AS case_result,
    tc.status AS case_status,
    tc.start_date AS case_start_date,
    tc.stop_date AS case_stop_date,
    m.description AS metric_description,
    m.result AS metric_result,
    m.status AS metric_status,
    meas.name AS measurement_name,
    meas.value AS measurement_value,
    meas.units AS measurement_units,
    meas.dut_name AS measurement_dut_name,
    meas.created_at
FROM test_runs tr
JOIN test_cases tc ON tr.id = tc.test_run_id
JOIN test_groups tg ON tc.group_id = tg.id
LEFT JOIN metrics m ON tc.id = m.test_case_id
LEFT JOIN measurements meas ON (m.id = meas.metric_id OR tc.id = meas.test_case_id);
