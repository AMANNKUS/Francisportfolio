-- Bellabeat case study: sleep-data coverage and calendar-day sleep analysis.
-- Continue from activity queries 1-7. Run each numbered query independently.
-- Missing sleep values remain missing. Coverage counts of zero indicate that
-- no sleep observations from the supplied source were available for that date.
-- Sleep was aggregated from timestamped minutes by calendar date; overnight
-- episodes can span dates. Do not label these summaries as nightly duration,
-- sleep quality, sleep efficiency, or the prevalence of insufficient sleep.
-- The original source table is queried without mutation.
-- Expected results were checked locally against the prepared CSV; execute the
-- SQL in BigQuery to verify the uploaded data.

-- 8. Sleep-data availability in the full table and the activity analysis cohort.
-- Percentages describe available records, not verified use or feature adoption.
WITH cohorts AS (
  SELECT
    'All available days' AS cohort,
    participant_id,
    sleep_minutes_recorded
  FROM `YOUR_PROJECT.FitBit_Fitness_Tracker.FitBit Fitness Tracker Data`

  UNION ALL

  SELECT
    'Full activity-coverage days' AS cohort,
    participant_id,
    sleep_minutes_recorded
  FROM `YOUR_PROJECT.FitBit_Fitness_Tracker.FitBit Fitness Tracker Data`
  WHERE minute_steps_minutes_recorded = 1440
    AND minute_calories_minutes_recorded = 1440
    AND minute_intensity_minutes_recorded = 1440
)
SELECT
  cohort,
  COUNT(*) AS available_participant_days,
  COUNT(DISTINCT participant_id) AS distinct_participant_ids,
  COUNTIF(sleep_minutes_recorded > 0) AS days_with_sleep_records,
  COUNT(DISTINCT IF(sleep_minutes_recorded > 0, participant_id, NULL))
    AS ids_with_sleep_records,
  ROUND(
    100.0 * SAFE_DIVIDE(COUNTIF(sleep_minutes_recorded > 0), COUNT(*)),
    1
  ) AS percentage_of_available_days_with_sleep_records
FROM cohorts
GROUP BY cohort
ORDER BY cohort;

-- 9. Recorded calendar-day sleep summaries under two weighting methods.
-- These values describe days with available sleep data, not complete nights.
WITH sleep_days AS (
  SELECT *
  FROM `YOUR_PROJECT.FitBit_Fitness_Tracker.FitBit Fitness Tracker Data`
  WHERE sleep_minutes_recorded > 0
),
participant_means AS (
  SELECT
    participant_id,
    COUNT(*) AS sleep_days,
    MIN(activity_date) AS first_sleep_record_date,
    MAX(activity_date) AS last_sleep_record_date,
    AVG(sleep_asleep_minutes) AS mean_asleep_minutes,
    AVG(sleep_restless_minutes) AS mean_restless_minutes,
    AVG(sleep_awake_minutes) AS mean_awake_minutes,
    AVG(sleep_minutes_recorded) AS mean_sleep_state_minutes
  FROM sleep_days
  GROUP BY participant_id
)
SELECT
  'Daily-record weighted' AS weighting_method,
  COUNT(*) AS participant_days_with_sleep,
  COUNT(DISTINCT participant_id) AS distinct_participant_ids,
  MIN(activity_date) AS first_sleep_record_date,
  MAX(activity_date) AS last_sleep_record_date,
  ROUND(AVG(sleep_asleep_minutes), 1) AS mean_recorded_asleep_minutes,
  ROUND(AVG(sleep_asleep_minutes) / 60.0, 2) AS mean_recorded_asleep_hours,
  ROUND(AVG(sleep_restless_minutes), 1) AS mean_recorded_restless_minutes,
  ROUND(AVG(sleep_awake_minutes), 1) AS mean_recorded_awake_minutes,
  ROUND(AVG(sleep_minutes_recorded), 1) AS mean_recorded_sleep_state_minutes
FROM sleep_days

UNION ALL

SELECT
  'Equal-ID weighted' AS weighting_method,
  SUM(sleep_days) AS participant_days_with_sleep,
  COUNT(*) AS distinct_participant_ids,
  MIN(first_sleep_record_date) AS first_sleep_record_date,
  MAX(last_sleep_record_date) AS last_sleep_record_date,
  ROUND(AVG(mean_asleep_minutes), 1) AS mean_recorded_asleep_minutes,
  ROUND(AVG(mean_asleep_minutes) / 60.0, 2) AS mean_recorded_asleep_hours,
  ROUND(AVG(mean_restless_minutes), 1) AS mean_recorded_restless_minutes,
  ROUND(AVG(mean_awake_minutes), 1) AS mean_recorded_awake_minutes,
  ROUND(AVG(mean_sleep_state_minutes), 1) AS mean_recorded_sleep_state_minutes
FROM participant_means
ORDER BY weighting_method;

-- 10. Participant sleep profiles and recording coverage.
-- Keep participants with sparse records visible rather than automatically
-- treating their averages as stable estimates of habitual sleep.
SELECT
  participant_id,
  COUNT(*) AS recorded_sleep_days,
  MIN(activity_date) AS first_sleep_record_date,
  MAX(activity_date) AS last_sleep_record_date,
  COUNTIF(minute_steps_minutes_recorded = 1440
    AND minute_calories_minutes_recorded = 1440
    AND minute_intensity_minutes_recorded = 1440) AS sleep_days_with_full_activity_coverage,
  ROUND(AVG(sleep_asleep_minutes), 1) AS mean_recorded_asleep_minutes,
  ROUND(AVG(sleep_asleep_minutes) / 60.0, 2) AS mean_recorded_asleep_hours,
  ROUND(AVG(sleep_restless_minutes), 1) AS mean_recorded_restless_minutes,
  ROUND(AVG(sleep_awake_minutes), 1) AS mean_recorded_awake_minutes,
  ROUND(AVG(sleep_minutes_recorded), 1) AS mean_recorded_sleep_state_minutes
FROM `YOUR_PROJECT.FitBit_Fitness_Tracker.FitBit Fitness Tracker Data`
WHERE sleep_minutes_recorded > 0
GROUP BY participant_id
ORDER BY recorded_sleep_days DESC, participant_id;

-- 11. Same-calendar-day activity/sleep association.
-- Sleep can include portions of different overnight episodes or naps.
-- This is not an analysis of sleep during a particular night or a causal test.
WITH matched_days AS (
  SELECT
    participant_id,
    minute_total_steps,
    sleep_asleep_minutes
  FROM `YOUR_PROJECT.FitBit_Fitness_Tracker.FitBit Fitness Tracker Data`
  WHERE minute_steps_minutes_recorded = 1440
    AND minute_calories_minutes_recorded = 1440
    AND minute_intensity_minutes_recorded = 1440
    AND sleep_minutes_recorded > 0
),
samples AS (
  SELECT 'All matched full-coverage days' AS sample, * FROM matched_days

  UNION ALL

  SELECT 'Positive-step matched full-coverage days' AS sample, *
  FROM matched_days
  WHERE minute_total_steps > 0
)
SELECT
  sample,
  COUNT(*) AS matched_participant_days,
  COUNT(DISTINCT participant_id) AS distinct_participant_ids,
  ROUND(AVG(minute_total_steps), 1) AS mean_daily_steps,
  ROUND(AVG(sleep_asleep_minutes), 1) AS mean_recorded_asleep_minutes,
  ROUND(
    CORR(
      CAST(minute_total_steps AS FLOAT64),
      CAST(sleep_asleep_minutes AS FLOAT64)
    ),
    3
  ) AS descriptive_same_day_step_sleep_correlation
FROM samples
GROUP BY sample
ORDER BY sample;

-- 12. Sleep-data availability by zero-step status in the activity cohort.
-- This checks whether availability differs with observed step recording.
-- It does not identify why sleep records or steps are missing.
SELECT
  CASE
    WHEN minute_total_steps = 0 THEN 'Zero-step days'
    WHEN minute_total_steps > 0 THEN 'Positive-step days'
    ELSE 'Other step values'
  END AS step_record_group,
  COUNT(*) AS participant_days,
  COUNT(DISTINCT participant_id) AS distinct_participant_ids,
  COUNTIF(sleep_minutes_recorded > 0) AS days_with_sleep_records,
  COUNT(DISTINCT IF(sleep_minutes_recorded > 0, participant_id, NULL))
    AS ids_with_sleep_records,
  ROUND(
    100.0 * SAFE_DIVIDE(COUNTIF(sleep_minutes_recorded > 0), COUNT(*)),
    1
  ) AS percentage_of_days_with_sleep_records
FROM `YOUR_PROJECT.FitBit_Fitness_Tracker.FitBit Fitness Tracker Data`
WHERE minute_steps_minutes_recorded = 1440
    AND minute_calories_minutes_recorded = 1440
    AND minute_intensity_minutes_recorded = 1440
GROUP BY step_record_group
ORDER BY step_record_group;
