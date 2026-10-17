-- 03_analysis.sql: one named result per block. The pipeline runs each block and exports it to
-- reports/tables/<name>.csv. Block header format:  -- name: <result_name>

-- name: data_quality
SELECT
    count(*)                                              AS requests,
    count(DISTINCT request_id)                            AS distinct_ids,
    sum(is_closed::INT)                                   AS closed,
    sum((NOT is_closed)::INT)                             AS still_open_at_snapshot,
    sum(dq_closed_before_created::INT)                    AS closed_before_created_excluded,
    sum((days_to_close = 0)::INT)                         AS closed_same_minute,
    sum((created_at IS NULL)::INT)                        AS missing_created,
    min(created_at)                                       AS first_created,
    max(created_at)                                       AS last_created,
    max(snapshot_at)                                      AS snapshot_at
FROM fct_requests_enriched;

-- name: kpi_overview
SELECT
    count(*)                                              AS requests,
    round(median(days_to_close), 2)                       AS median_days,
    round(quantile_cont(days_to_close, 0.9), 1)           AS p90_days,
    round(sum(days_to_close))                             AS total_request_days,
    round(100.0 * avg((outcome = 'Outcome not published')::INT), 1) AS pct_outcome_not_published
FROM fct_requests_enriched;

-- name: pareto_request_days
-- Where does citizens' waiting time accumulate? Sum of days-to-close by complaint type.
WITH by_type AS (
    SELECT complaint_type, count(*) AS requests,
           round(median(days_to_close), 1) AS median_days,
           round(quantile_cont(days_to_close, 0.9), 1) AS p90_days,
           sum(days_to_close) AS request_days
    FROM fct_requests_enriched WHERE days_to_close IS NOT NULL
    GROUP BY 1
)
SELECT *,
       round(100.0 * request_days / sum(request_days) OVER (), 2) AS pct_request_days,
       round(100.0 * sum(request_days) OVER (ORDER BY request_days DESC ROWS UNBOUNDED PRECEDING)
             / sum(request_days) OVER (), 2) AS cum_pct_request_days,
       round(100.0 * requests / sum(requests) OVER (), 2) AS pct_requests
FROM by_type ORDER BY request_days DESC;

-- name: outcome_mix
SELECT complaint_type, outcome, count(*) AS requests,
       round(100.0 * count(*) / sum(count(*)) OVER (PARTITION BY complaint_type), 1) AS pct_of_type,
       round(median(days_to_close), 2) AS median_days
FROM fct_requests_enriched
GROUP BY 1, 2 ORDER BY complaint_type, requests DESC;

-- name: street_light_tail
-- Street Light Out: distribution of time-to-close and where the waiting days sit.
SELECT
    CASE WHEN days_to_close <= 1 THEN '1: <=1 day'
         WHEN days_to_close <= 7 THEN '2: 1-7 days'
         WHEN days_to_close <= 30 THEN '3: 7-30 days'
         WHEN days_to_close <= 90 THEN '4: 30-90 days'
         ELSE '5: >90 days' END                           AS age_band,
    count(*)                                              AS requests,
    round(sum(days_to_close))                             AS request_days,
    round(100.0 * count(*) / sum(count(*)) OVER (), 1)    AS pct_requests,
    round(100.0 * sum(days_to_close) / sum(sum(days_to_close)) OVER (), 1) AS pct_request_days
FROM fct_requests_enriched
WHERE complaint_type = 'Street Light Condition' AND descriptor = 'Street Light Out' AND days_to_close IS NOT NULL
GROUP BY 1 ORDER BY 1;

-- name: street_light_by_borough
SELECT borough, count(*) AS requests,
       round(median(days_to_close), 1) AS median_days,
       round(quantile_cont(days_to_close, 0.9), 1) AS p90_days,
       round(100.0 * avg((days_to_close > 30)::INT), 1) AS pct_over_30_days
FROM fct_requests_enriched
WHERE complaint_type = 'Street Light Condition' AND descriptor = 'Street Light Out'
  AND days_to_close IS NOT NULL AND borough <> 'Unspecified'
GROUP BY 1 ORDER BY p90_days DESC;

-- name: street_light_by_month
SELECT created_month, count(*) AS requests,
       round(median(days_to_close), 1) AS median_days,
       round(quantile_cont(days_to_close, 0.9), 1) AS p90_days,
       round(100.0 * avg((days_to_close > 30)::INT), 1) AS pct_over_30_days
FROM fct_requests_enriched
WHERE complaint_type = 'Street Light Condition' AND descriptor = 'Street Light Out' AND days_to_close IS NOT NULL
GROUP BY 1 ORDER BY 1;

-- name: open_backlog
-- 2025 requests still open at the snapshot, by type (right-censored: true durations are longer).
SELECT complaint_type, count(*) AS open_requests,
       round(median(open_age_days)) AS median_age_days,
       round(quantile_cont(open_age_days, 0.9)) AS p90_age_days
FROM fct_requests_enriched WHERE NOT is_closed
GROUP BY 1 ORDER BY open_requests DESC;

-- name: street_condition_by_descriptor
-- Failure demand by descriptor for Street Condition (the only high-volume type with published outcomes).
SELECT descriptor, count(*) AS requests,
       round(100.0 * avg((outcome = 'Repaired / completed')::INT), 1)     AS pct_repaired,
       round(100.0 * avg((outcome = 'No defect found')::INT), 1)          AS pct_no_defect,
       round(100.0 * avg((outcome = 'Wrong agency / referred')::INT), 1)  AS pct_wrong_agency,
       round(100.0 * avg((outcome = 'Duplicate')::INT), 1)                AS pct_duplicate,
       round(100.0 * avg(is_failure_demand::INT), 1)                      AS pct_failure_demand,
       sum(is_failure_demand::INT)                                        AS failure_demand_requests,
       round(median(days_to_close), 2)                                    AS median_days
FROM fct_requests_enriched
WHERE complaint_type = 'Street Condition'
GROUP BY 1 HAVING count(*) >= 250 ORDER BY failure_demand_requests DESC;

-- name: failure_demand_by_type
SELECT complaint_type, count(*) AS requests,
       sum(is_failure_demand::INT) AS failure_demand_requests,
       round(100.0 * avg(is_failure_demand::INT), 1) AS pct_failure_demand,
       round(100.0 * avg((outcome = 'Outcome not published')::INT), 1) AS pct_outcome_not_published
FROM fct_requests_enriched
GROUP BY 1 HAVING count(*) >= 2000 ORDER BY requests DESC;
