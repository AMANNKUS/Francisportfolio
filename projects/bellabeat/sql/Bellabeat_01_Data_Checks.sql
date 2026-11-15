-- Bellabeat case study: check the imported merged daily table.
-- Run the statements individually and retain each result for the audit trail.
-- These queries inspect data without changing the source table.

-- 1. Import overview and missing merge keys.
SELECT
  COUNT(*) AS total_rows,
  COUNT(DISTINCT participant_id) AS distinct_participant_ids,
  MIN(activity_date) AS first_date,
  MAX(activity_date) AS last_date,
  COUNTIF(participant_id IS NULL) AS missing_participant_ids,
  COUNTIF(activity_date IS NULL) AS missing_activity_dates
FROM
  `YOUR_PROJECT.FitBit_Fitness_Tracker.FitBit Fitness Tracker Data`;

-- 2. Duplicate participant-date keys. No returned rows means no duplicates.
SELECT
  participant_id,
  activity_date,
  COUNT(*) AS rows_per_participant_date
FROM
  `YOUR_PROJECT.FitBit_Fitness_Tracker.FitBit Fitness Tracker Data`
GROUP BY
  participant_id,
  activity_date
HAVING
  COUNT(*) > 1
ORDER BY
  participant_id,
  activity_date;

-- 3. Coverage by measure. These are counts of participant-days, not calendar
-- dates or independent people. A day with sleep records need not be a full night.
SELECT
  COUNTIF(has_daily_activity) AS days_with_original_daily_activity,
  COUNTIF(minute_steps_minutes_recorded > 0) AS days_with_minute_steps,
  COUNT(DISTINCT IF(minute_steps_minutes_recorded > 0, participant_id, NULL)) AS ids_with_minute_steps,
  COUNTIF(
    minute_steps_minutes_recorded = 1440
    AND minute_calories_minutes_recorded = 1440
    AND minute_intensity_minutes_recorded = 1440
  ) AS days_with_full_activity_record_coverage,
  COUNTIF(sleep_minutes_recorded > 0) AS days_with_sleep_records,
  COUNT(DISTINCT IF(sleep_minutes_recorded > 0, participant_id, NULL)) AS ids_with_sleep_records,
  COUNTIF(heart_rate_readings > 0) AS days_with_heart_rate_records,
  COUNT(DISTINCT IF(heart_rate_readings > 0, participant_id, NULL)) AS ids_with_heart_rate_records,
  COUNTIF(weight_readings > 0) AS days_with_weight_records,
  COUNT(DISTINCT IF(weight_readings > 0, participant_id, NULL)) AS ids_with_weight_records
FROM
  `YOUR_PROJECT.FitBit_Fitness_Tracker.FitBit Fitness Tracker Data`;

-- 4. Quality flags. Investigate flagged records; do not automatically delete
-- zero-step days or replace missing activity/sleep/weight values with zero.
SELECT
  COUNTIF(
    daily_total_steps < 0
    OR hourly_total_steps < 0
    OR minute_total_steps < 0
  ) AS rows_with_negative_steps,
  COUNTIF(
    minute_steps_minutes_recorded < 0
    OR minute_steps_minutes_recorded > 1440
    OR minute_calories_minutes_recorded < 0
    OR minute_calories_minutes_recorded > 1440
    OR minute_intensity_minutes_recorded < 0
    OR minute_intensity_minutes_recorded > 1440
    OR minute_mets_minutes_recorded < 0
    OR minute_mets_minutes_recorded > 1440
  ) AS rows_with_invalid_activity_minute_counts,
  COUNTIF(
    hourly_steps_hours_recorded < 0
    OR hourly_steps_hours_recorded > 24
    OR hourly_calories_hours_recorded < 0
    OR hourly_calories_hours_recorded > 24
    OR hourly_intensity_hours_recorded < 0
    OR hourly_intensity_hours_recorded > 24
  ) AS rows_with_invalid_activity_hour_counts,
  COUNTIF(
    sleep_minutes_recorded > 0
    AND (
      sleep_asleep_minutes IS NULL
      OR sleep_restless_minutes IS NULL
      OR sleep_awake_minutes IS NULL
      OR sleep_asleep_minutes + sleep_restless_minutes + sleep_awake_minutes != sleep_minutes_recorded
    )
  ) AS rows_with_inconsistent_sleep_counts,
  COUNTIF(
    minute_steps_minutes_recorded = 1440
    AND minute_calories_minutes_recorded = 1440
    AND minute_intensity_minutes_recorded = 1440
    AND minute_total_steps = 0
  ) AS full_coverage_zero_step_days_to_review,
  COUNTIF(has_daily_activity AND daily_calories_kcal = 0) AS original_daily_zero_calorie_rows_to_review
FROM
  `YOUR_PROJECT.FitBit_Fitness_Tracker.FitBit Fitness Tracker Data`;
