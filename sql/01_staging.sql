-- 01_staging.sql: typed, cleaned copy of the raw NYC 311 extract (one row per service request).
-- Inputs : raw_csv_path and snapshot_ts are substituted by the pipeline (see src/case_study/pipeline.py).
CREATE OR REPLACE TABLE stg_requests AS
WITH raw AS (
    SELECT * FROM read_csv('{raw_csv_path}', header = true, all_varchar = true)
)
SELECT
    CAST(unique_key AS BIGINT)                                     AS request_id,
    TRY_CAST(created_date AS TIMESTAMP)                            AS created_at,
    TRY_CAST(closed_date AS TIMESTAMP)                             AS closed_at,
    TRY_CAST(resolution_action_updated_date AS TIMESTAMP)          AS last_action_at,
    agency,
    complaint_type,
    COALESCE(NULLIF(descriptor, ''), 'Unspecified')                AS descriptor,
    status,
    -- The source double-encodes some apostrophes/quotes (UTF-8 read as Latin-1); repair them.
    regexp_replace(resolution_description, 'â[\x{80}-\x{9f}]+', '''', 'g') AS resolution_description,
    COALESCE(NULLIF(borough, ''), 'Unspecified')                   AS borough,
    COALESCE(NULLIF(open_data_channel_type, ''), 'UNKNOWN')        AS channel,
    community_board,
    incident_zip
FROM raw;

-- Request-level facts used by every analysis.
CREATE OR REPLACE TABLE fct_requests AS
SELECT
    r.*,
    TIMESTAMP '{snapshot_ts}'                                       AS snapshot_at,
    closed_at IS NOT NULL                                           AS is_closed,
    -- Data-quality flag: closure stamped before creation (excluded from duration stats).
    closed_at IS NOT NULL AND closed_at < created_at                AS dq_closed_before_created,
    CASE WHEN closed_at >= created_at
         THEN date_diff('minute', created_at, closed_at) / 1440.0 END   AS days_to_close,
    -- For still-open requests: age at the snapshot (a lower bound on their eventual duration).
    CASE WHEN closed_at IS NULL
         THEN date_diff('minute', created_at, TIMESTAMP '{snapshot_ts}') / 1440.0 END AS open_age_days,
    month(created_at)                                               AS created_month
FROM stg_requests r;
