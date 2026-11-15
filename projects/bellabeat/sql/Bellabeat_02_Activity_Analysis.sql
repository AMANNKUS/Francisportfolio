-- Bellabeat case study: activity analysis using the merged daily table.
-- Run each numbered query independently in BigQuery.
-- Main sample: 1,440 exported minutes for steps, calories, and intensity.
-- Export coverage does not establish all-day device wear.
-- Original daily/hourly totals are alternative source summaries; do not add
-- them to the minute-derived totals used here.
-- Intensity-zero minutes can include sleep and non-wear; they are not a
-- measure of waking sitting time.
-- Calorie figures are estimated total energy expenditure, not exercise-only
-- calories. Activity-intensity categories are device classifications.
-- Local CSV checks provide expected results; these statements have not been
-- executed here against the user's BigQuery project.

-- 1. Overall descriptive summary. Each participant-day has equal weight.
WITH analysis_days AS (
  SELECT
    *,
    minute_lightly_active_minutes + minute_fairly_active_minutes
      + minute_very_active_minutes AS recorded_active_minutes,
    minute_fairly_active_minutes + minute_very_active_minutes
      AS recorded_fairly_or_very_active_minutes
  FROM
    `YOUR_PROJECT.FitBit_Fitness_Tracker.FitBit Fitness Tracker Data`
  WHERE
    minute_steps_minutes_recorded = 1440
    AND minute_calories_minutes_recorded = 1440
    AND minute_intensity_minutes_recorded = 1440
),
daily_summary AS (
  SELECT
    COUNT(*) AS participant_days,
    COUNT(DISTINCT participant_id) AS distinct_participant_ids,
    MIN(activity_date) AS first_analysis_date,
    MAX(activity_date) AS last_analysis_date,
    ROUND(AVG(minute_total_steps), 1) AS mean_daily_steps,
    ROUND(AVG(minute_total_calories_kcal), 1) AS mean_daily_calories_kcal,
    ROUND(AVG(minute_lightly_active_minutes), 1) AS mean_lightly_active_minutes,
    ROUND(AVG(minute_fairly_active_minutes), 1) AS mean_fairly_active_minutes,
    ROUND(AVG(minute_very_active_minutes), 1) AS mean_very_active_minutes,
    ROUND(AVG(recorded_active_minutes), 1) AS mean_recorded_active_minutes,
    ROUND(AVG(recorded_fairly_or_very_active_minutes), 1)
      AS mean_fairly_or_very_active_minutes,
    COUNTIF(minute_total_steps = 0) AS zero_step_days,
    ROUND(100.0 * SAFE_DIVIDE(COUNTIF(minute_total_steps = 0), COUNT(*)), 1)
      AS zero_step_day_percentage
  FROM analysis_days
),
step_median AS (
  SELECT DISTINCT
    PERCENTILE_CONT(CAST(minute_total_steps AS FLOAT64), 0.5) OVER ()
      AS median_daily_steps
  FROM analysis_days
)
SELECT
  s.*,
  m.median_daily_steps
FROM daily_summary AS s
LEFT JOIN step_median AS m ON TRUE;

-- 2. Participant profiles. Zero-step days remain in the main mean.
-- The positive-step mean is a sensitivity measure for the same participant.
WITH analysis_days AS (
  SELECT
    *,
    minute_lightly_active_minutes + minute_fairly_active_minutes
      + minute_very_active_minutes AS recorded_active_minutes,
    minute_fairly_active_minutes + minute_very_active_minutes
      AS recorded_fairly_or_very_active_minutes
  FROM
    `YOUR_PROJECT.FitBit_Fitness_Tracker.FitBit Fitness Tracker Data`
  WHERE
    minute_steps_minutes_recorded = 1440
    AND minute_calories_minutes_recorded = 1440
    AND minute_intensity_minutes_recorded = 1440
)
SELECT
  participant_id,
  COUNT(*) AS recorded_days,
  MIN(activity_date) AS first_analysis_date,
  MAX(activity_date) AS last_analysis_date,
  COUNTIF(minute_total_steps = 0) AS zero_step_days,
  ROUND(100.0 * SAFE_DIVIDE(COUNTIF(minute_total_steps = 0), COUNT(*)), 1)
    AS zero_step_day_percentage,
  ROUND(AVG(minute_total_steps), 1) AS mean_daily_steps,
  ROUND(AVG(IF(minute_total_steps > 0, minute_total_steps, NULL)), 1)
    AS mean_steps_on_positive_step_days,
  ROUND(AVG(minute_total_calories_kcal), 1) AS mean_daily_calories_kcal,
  ROUND(AVG(recorded_active_minutes), 1) AS mean_recorded_active_minutes,
  ROUND(AVG(recorded_fairly_or_very_active_minutes), 1)
    AS mean_fairly_or_very_active_minutes
FROM analysis_days
GROUP BY participant_id
ORDER BY mean_daily_steps DESC, participant_id;

-- 3. Equal-participant-weighted summary.
-- First calculate each participant's mean, then average the participant means.
WITH analysis_days AS (
  SELECT
    *,
    minute_lightly_active_minutes + minute_fairly_active_minutes
      + minute_very_active_minutes AS recorded_active_minutes,
    minute_fairly_active_minutes + minute_very_active_minutes
      AS recorded_fairly_or_very_active_minutes
  FROM
    `YOUR_PROJECT.FitBit_Fitness_Tracker.FitBit Fitness Tracker Data`
  WHERE
    minute_steps_minutes_recorded = 1440
    AND minute_calories_minutes_recorded = 1440
    AND minute_intensity_minutes_recorded = 1440
),
participant_means AS (
  SELECT
    participant_id,
    COUNT(*) AS recorded_days,
    AVG(minute_total_steps) AS mean_steps,
    AVG(minute_total_calories_kcal) AS mean_calories_kcal,
    AVG(recorded_active_minutes) AS mean_active_minutes,
    AVG(recorded_fairly_or_very_active_minutes) AS mean_fairly_or_very_active_minutes
  FROM analysis_days
  GROUP BY participant_id
)
SELECT
  COUNT(*) AS distinct_participant_ids,
  SUM(recorded_days) AS participant_days,
  MIN(recorded_days) AS fewest_recorded_days_per_id,
  MAX(recorded_days) AS most_recorded_days_per_id,
  ROUND(AVG(mean_steps), 1) AS equal_id_weighted_mean_daily_steps,
  ROUND(AVG(mean_calories_kcal), 1) AS equal_id_weighted_mean_daily_calories_kcal,
  ROUND(AVG(mean_active_minutes), 1) AS equal_id_weighted_mean_active_minutes,
  ROUND(AVG(mean_fairly_or_very_active_minutes), 1)
    AS equal_id_weighted_mean_fairly_or_very_active_minutes
FROM participant_means;

-- 4. Weekday patterns, giving each participant equal weight within a weekday.
-- Weekday order is Monday=1 through Sunday=7.
WITH analysis_days AS (
  SELECT
    *,
    minute_lightly_active_minutes + minute_fairly_active_minutes
      + minute_very_active_minutes AS recorded_active_minutes,
    minute_fairly_active_minutes + minute_very_active_minutes
      AS recorded_fairly_or_very_active_minutes
  FROM
    `YOUR_PROJECT.FitBit_Fitness_Tracker.FitBit Fitness Tracker Data`
  WHERE
    minute_steps_minutes_recorded = 1440
    AND minute_calories_minutes_recorded = 1440
    AND minute_intensity_minutes_recorded = 1440
),
participant_weekday_means AS (
  SELECT
    participant_id,
    MOD(EXTRACT(DAYOFWEEK FROM activity_date) + 5, 7) + 1 AS weekday_order,
    FORMAT_DATE('%A', activity_date) AS weekday,
    COUNT(*) AS recorded_days,
    AVG(minute_total_steps) AS mean_steps,
    AVG(recorded_active_minutes) AS mean_active_minutes,
    AVG(recorded_fairly_or_very_active_minutes) AS mean_fairly_or_very_active_minutes
  FROM analysis_days
  GROUP BY participant_id, weekday_order, weekday
)
SELECT
  weekday_order,
  weekday,
  COUNT(*) AS distinct_participant_ids,
  SUM(recorded_days) AS participant_days,
  ROUND(AVG(mean_steps), 1) AS equal_id_weighted_mean_steps,
  ROUND(AVG(mean_active_minutes), 1) AS equal_id_weighted_mean_active_minutes,
  ROUND(AVG(mean_fairly_or_very_active_minutes), 1)
    AS equal_id_weighted_mean_fairly_or_very_active_minutes
FROM participant_weekday_means
GROUP BY weekday_order, weekday
ORDER BY weekday_order;

-- 5. Paired weekday/weekend comparison.
-- Each participant contributes one weekday mean and one weekend mean.
WITH analysis_days AS (
  SELECT
    *,
    minute_lightly_active_minutes + minute_fairly_active_minutes
      + minute_very_active_minutes AS recorded_active_minutes,
    minute_fairly_active_minutes + minute_very_active_minutes
      AS recorded_fairly_or_very_active_minutes
  FROM
    `YOUR_PROJECT.FitBit_Fitness_Tracker.FitBit Fitness Tracker Data`
  WHERE
    minute_steps_minutes_recorded = 1440
    AND minute_calories_minutes_recorded = 1440
    AND minute_intensity_minutes_recorded = 1440
),
participant_week_means AS (
  SELECT
    participant_id,
    AVG(IF(EXTRACT(DAYOFWEEK FROM activity_date) NOT IN (1, 7),
      minute_total_steps, NULL)) AS weekday_mean_steps,
    AVG(IF(EXTRACT(DAYOFWEEK FROM activity_date) IN (1, 7),
      minute_total_steps, NULL)) AS weekend_mean_steps
  FROM analysis_days
  GROUP BY participant_id
)
SELECT
  COUNT(*) AS participant_ids_with_both_week_parts,
  ROUND(AVG(weekday_mean_steps), 1) AS equal_id_weighted_weekday_steps,
  ROUND(AVG(weekend_mean_steps), 1) AS equal_id_weighted_weekend_steps,
  ROUND(AVG(weekend_mean_steps - weekday_mean_steps), 1)
    AS mean_weekend_minus_weekday_steps
FROM participant_week_means
WHERE weekday_mean_steps IS NOT NULL
  AND weekend_mean_steps IS NOT NULL;

-- 6. Zero-step sensitivity analysis.
-- A positive-step filter is not proof of valid device wear; compare both rows.
WITH analysis_days AS (
  SELECT
    *,
    minute_lightly_active_minutes + minute_fairly_active_minutes
      + minute_very_active_minutes AS recorded_active_minutes,
    minute_fairly_active_minutes + minute_very_active_minutes
      AS recorded_fairly_or_very_active_minutes
  FROM
    `YOUR_PROJECT.FitBit_Fitness_Tracker.FitBit Fitness Tracker Data`
  WHERE
    minute_steps_minutes_recorded = 1440
    AND minute_calories_minutes_recorded = 1440
    AND minute_intensity_minutes_recorded = 1440
),
samples AS (
  SELECT 'All full-coverage days' AS sample, * FROM analysis_days
  UNION ALL
  SELECT 'Positive-step full-coverage days' AS sample, *
  FROM analysis_days
  WHERE minute_total_steps > 0
)
SELECT
  sample,
  COUNT(*) AS participant_days,
  COUNT(DISTINCT participant_id) AS distinct_participant_ids,
  COUNTIF(minute_total_steps = 0) AS zero_step_days,
  ROUND(AVG(minute_total_steps), 1) AS mean_daily_steps,
  ROUND(AVG(minute_total_calories_kcal), 1) AS mean_daily_calories_kcal,
  ROUND(AVG(recorded_active_minutes), 1) AS mean_recorded_active_minutes,
  ROUND(AVG(recorded_fairly_or_very_active_minutes), 1)
    AS mean_fairly_or_very_active_minutes
FROM samples
GROUP BY sample
ORDER BY CASE WHEN sample = 'All full-coverage days' THEN 1 ELSE 2 END;

-- 7. Descriptive step/calorie association with zero-step sensitivity.
-- Repeated days from the same participant are not independent observations.
-- No causal conclusion or significance test is implied by these correlations.
WITH analysis_days AS (
  SELECT
    *,
    minute_lightly_active_minutes + minute_fairly_active_minutes
      + minute_very_active_minutes AS recorded_active_minutes,
    minute_fairly_active_minutes + minute_very_active_minutes
      AS recorded_fairly_or_very_active_minutes
  FROM
    `YOUR_PROJECT.FitBit_Fitness_Tracker.FitBit Fitness Tracker Data`
  WHERE
    minute_steps_minutes_recorded = 1440
    AND minute_calories_minutes_recorded = 1440
    AND minute_intensity_minutes_recorded = 1440
),
samples AS (
  SELECT 'All full-coverage days' AS sample, * FROM analysis_days
  UNION ALL
  SELECT 'Positive-step full-coverage days' AS sample, *
  FROM analysis_days
  WHERE minute_total_steps > 0
)
SELECT
  sample,
  COUNT(*) AS participant_days,
  COUNT(DISTINCT participant_id) AS distinct_participant_ids,
  ROUND(CORR(CAST(minute_total_steps AS FLOAT64), minute_total_calories_kcal), 3)
    AS descriptive_step_calorie_correlation
FROM samples
GROUP BY sample
ORDER BY CASE WHEN sample = 'All full-coverage days' THEN 1 ELSE 2 END;
