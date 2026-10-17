-- 02_outcomes.sql: map DOT's free-text resolution descriptions to 9 standard outcome classes.
-- Order matters: the first matching rule wins. Rules were written by reading every description
-- with 100+ occurrences; tests/test_outcomes.py pins examples for each class.
CREATE OR REPLACE TABLE fct_requests_outcome AS
SELECT
    f.*,
    CASE
        WHEN resolution_description IS NULL OR trim(resolution_description) = '' THEN 'No resolution text'
        WHEN resolution_description ILIKE '%duplicate%' THEN 'Duplicate'
        WHEN resolution_description ILIKE '%not within its jurisdiction%'
          OR resolution_description ILIKE '%not to be under%jurisdiction%'
          OR resolution_description ILIKE '%outside New York City''s jurisdiction%'
          OR resolution_description ILIKE '%requested the Department of Environmental Protection%'
          OR resolution_description ILIKE '%asked the Department of Environmental Protection%'
          OR resolution_description ILIKE '%referred to the Department of%'
          OR resolution_description ILIKE '%does not handle this type of complaint%'
          OR resolution_description ILIKE '%issue you reported is a %issue%' THEN 'Wrong agency / referred'
        WHEN resolution_description ILIKE '%did not have sufficient information%' THEN 'Insufficient information'
        WHEN resolution_description ILIKE '%could not find%'
          OR resolution_description ILIKE '%did not find%'
          OR resolution_description ILIKE '%not found, therefore no action%'
          OR resolution_description ILIKE '%did not see a violation%'
          OR resolution_description ILIKE '%meets its standards%'
          OR resolution_description ILIKE '%meets DOT standards%'
          OR resolution_description ILIKE '%in compliance with%'
          OR resolution_description ILIKE '%found that the problem was fixed%'
          OR resolution_description ILIKE '%not hazardous%' THEN 'No defect found'
        WHEN resolution_description ILIKE '%Corrective Action Repair%'
          OR resolution_description ILIKE '%summons%'
          OR resolution_description ILIKE '%property owner%'
          OR resolution_description ILIKE '%responsible party%'
          OR resolution_description ILIKE '%sidewalk dismissal%'
          OR resolution_description ILIKE '%permit of record%' THEN 'Third party must repair'
        WHEN resolution_description ILIKE '%resurfacing%'
          OR resolution_description ILIKE '%curb contract%'
          OR resolution_description ILIKE '%curb construction contract%'
          OR resolution_description ILIKE '%reconstruction project%'
          OR resolution_description ILIKE '%processed into another system%'
          OR resolution_description ILIKE '%next scheduled maintenance%' THEN 'Deferred to planned work'
        WHEN resolution_description ILIKE '%repaired%'
          OR resolution_description ILIKE '%completed%'
          OR resolution_description ILIKE '%corrected the condition%'
          OR resolution_description ILIKE '%temporary repairs%'
          OR resolution_description ILIKE '%was removed%'
          OR resolution_description ILIKE '%removed the%' THEN 'Repaired / completed'
        WHEN resolution_description ILIKE '%available on the Department of Transportation%'
          OR resolution_description ILIKE '%not available online%'
          OR resolution_description ILIKE '%Notes to Customer%'
          OR resolution_description ILIKE '%see customer notes%' THEN 'Outcome not published'
        ELSE 'Other'
    END AS outcome
FROM fct_requests f;

-- "Failure demand": requests where a DOT inspection or handling step produced no repair by DOT
-- because the job should never have entered DOT's queue in that form.
CREATE OR REPLACE VIEW fct_requests_enriched AS
SELECT *,
       outcome IN ('No defect found', 'Wrong agency / referred', 'Duplicate', 'Insufficient information')
           AS is_failure_demand
FROM fct_requests_outcome;
