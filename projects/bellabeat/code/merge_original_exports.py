"""Create a participant-calendar-day CSV from the eleven supplied Fitbit files."""
from pathlib import Path
import csv
import json
import re
import numpy as np
import pandas as pd

import argparse
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input-dir', type=Path, required=True)
parser.add_argument('--output', type=Path, default=Path('data/Fitbit_Daily_Merged.csv'))
args = parser.parse_args()
INPUT = args.input_dir
OUTPUT = args.output
ROOT = OUTPUT.parent
KEYS = ['participant_id', 'activity_date']
frames = []
source_audit = {}
integer_columns = set()
coverage_columns = set()
all_source_keys = set()
controls = []

def load(filename, time_column, *, daily=False, sleep=False):
    d = pd.read_csv(INPUT / filename, dtype={'Id': 'string', 'LogId': 'string', 'logId': 'string'})
    raw_rows = len(d)
    duplicates = int(d.duplicated().sum())
    if duplicates:
        assert sleep, f'Unexpected duplicate records in {filename}'
        d = d.drop_duplicates().copy()
    assert not d.duplicated(['Id', time_column]).any(), f'Conflicting observation timestamps: {filename}'
    assert d['Id'].notna().all() and d['Id'].str.fullmatch(r'\d+').all()
    d = d.rename(columns={'Id': 'participant_id'})
    d['_time'] = pd.to_datetime(d[time_column], format='%m/%d/%Y' if daily else '%m/%d/%Y %I:%M:%S %p', errors='raise')
    d['activity_date'] = d['_time'].dt.normalize()
    unique_keys = set(d[KEYS].itertuples(index=False, name=None))
    all_source_keys.update(unique_keys)
    source_audit[filename] = {
        'input_rows': raw_rows,
        'exact_duplicates_removed': duplicates,
        'retained_rows': len(d),
        'participants': int(d.participant_id.nunique()),
        'participant_days': len(unique_keys),
        'first_date': d.activity_date.min().strftime('%Y-%m-%d'),
        'last_date': d.activity_date.max().strftime('%Y-%m-%d'),
    }
    return d

def add(frame, integers=(), coverage=()):
    assert frame.index.is_unique
    frames.append(frame)
    integer_columns.update(integers)
    coverage_columns.update(coverage)

def reconcile(output_column, expected, *, absolute_tolerance=1e-7):
    controls.append((output_column, float(expected), absolute_tolerance))

# Preserve all supplied daily values. Prefixes keep measures from different
# source resolutions separate, rather than adding alternative summaries.
d = load('dailyActivity_merged.csv', 'ActivityDate', daily=True)
daily_names = {
    'TotalSteps': 'daily_total_steps',
    'TotalDistance': 'daily_total_distance',
    'TrackerDistance': 'daily_tracker_distance',
    'LoggedActivitiesDistance': 'daily_logged_activities_distance',
    'VeryActiveDistance': 'daily_very_active_distance',
    'ModeratelyActiveDistance': 'daily_moderately_active_distance',
    'LightActiveDistance': 'daily_light_active_distance',
    'SedentaryActiveDistance': 'daily_sedentary_active_distance',
    'VeryActiveMinutes': 'daily_very_active_minutes',
    'FairlyActiveMinutes': 'daily_fairly_active_minutes',
    'LightlyActiveMinutes': 'daily_lightly_active_minutes',
    'SedentaryMinutes': 'daily_sedentary_minutes',
    'Calories': 'daily_calories_kcal',
}
f = d.set_index(KEYS)[list(daily_names)].rename(columns=daily_names)
f['has_daily_activity'] = True
daily_integer = [daily_names[c] for c in ['TotalSteps', 'VeryActiveMinutes', 'FairlyActiveMinutes', 'LightlyActiveMinutes', 'SedentaryMinutes', 'Calories']]
add(f, daily_integer)
for c, out in daily_names.items():
    reconcile(out, d[c].sum())

# Independently aggregate each hourly/minute stream; never multiply records by
# joining detailed source rows directly.
simple_sources = [
    ('hourlySteps_merged.csv', 'ActivityHour', 'StepTotal', 'hourly_total_steps', 'hourly_steps_hours_recorded', True),
    ('hourlyCalories_merged.csv', 'ActivityHour', 'Calories', 'hourly_total_calories_kcal', 'hourly_calories_hours_recorded', True),
    ('minuteStepsNarrow_merged.csv', 'ActivityMinute', 'Steps', 'minute_total_steps', 'minute_steps_minutes_recorded', True),
    ('minuteCaloriesNarrow_merged.csv', 'ActivityMinute', 'Calories', 'minute_total_calories_kcal', 'minute_calories_minutes_recorded', False),
]
for filename, time_col, value_col, output_col, count_col, is_integer in simple_sources:
    d = load(filename, time_col)
    f = d.groupby(KEYS).agg(**{output_col: (value_col, 'sum'), count_col: (value_col, 'size')})
    add(f, [count_col] + ([output_col] if is_integer else []), [count_col])
    reconcile(output_col, d[value_col].sum(), absolute_tolerance=1e-6)
    reconcile(count_col, len(d), absolute_tolerance=0)
    print(f'Aggregated {filename}: {len(d):,} observations', flush=True)

d = load('hourlyIntensities_merged.csv', 'ActivityHour')
f = d.groupby(KEYS).agg(
    hourly_total_intensity=('TotalIntensity', 'sum'),
    hourly_mean_intensity=('AverageIntensity', 'mean'),
    hourly_intensity_hours_recorded=('TotalIntensity', 'size'),
)
add(f, ['hourly_total_intensity', 'hourly_intensity_hours_recorded'], ['hourly_intensity_hours_recorded'])
reconcile('hourly_total_intensity', d.TotalIntensity.sum())
reconcile('hourly_intensity_hours_recorded', len(d), absolute_tolerance=0)

d = load('minuteIntensitiesNarrow_merged.csv', 'ActivityMinute')
assert set(d.Intensity.unique()) <= {0, 1, 2, 3}
for code, label in enumerate(['sedentary', 'lightly_active', 'fairly_active', 'very_active']):
    d[label] = d.Intensity.eq(code).astype('int8')
f = d.groupby(KEYS).agg(
    minute_mean_intensity=('Intensity', 'mean'),
    minute_sedentary_minutes=('sedentary', 'sum'),
    minute_lightly_active_minutes=('lightly_active', 'sum'),
    minute_fairly_active_minutes=('fairly_active', 'sum'),
    minute_very_active_minutes=('very_active', 'sum'),
    minute_intensity_minutes_recorded=('Intensity', 'size'),
)
add(f, f.columns.difference(['minute_mean_intensity']), ['minute_intensity_minutes_recorded'])
for label in ['sedentary', 'lightly_active', 'fairly_active', 'very_active']:
    reconcile(f'minute_{label}_minutes', d[label].sum(), absolute_tolerance=0)
reconcile('minute_intensity_minutes_recorded', len(d), absolute_tolerance=0)

d = load('minuteMETsNarrow_merged.csv', 'ActivityMinute')
# Fitabase exports METs multiplied by ten; report conventional MET units.
d['_mets'] = d.METs / 10.0
f = d.groupby(KEYS).agg(
    minute_mean_mets=('_mets', 'mean'),
    minute_max_mets=('_mets', 'max'),
    minute_mets_minutes_recorded=('_mets', 'size'),
)
add(f, ['minute_mets_minutes_recorded'], ['minute_mets_minutes_recorded'])
reconcile('minute_mets_minutes_recorded', len(d), absolute_tolerance=0)
mets_control = float(d['_mets'].sum())

d = load('minuteSleep_merged.csv', 'date', sleep=True)
assert set(d.value.unique()) <= {1, 2, 3}
for code, label in [(1, 'asleep'), (2, 'restless'), (3, 'awake')]:
    d[label] = d.value.eq(code).astype('int8')
# Use the date of each recorded minute, splitting overnight episodes at
# midnight. These are calendar-day totals, not a night/episode attribution.
f = d.groupby(KEYS).agg(
    sleep_asleep_minutes=('asleep', 'sum'),
    sleep_restless_minutes=('restless', 'sum'),
    sleep_awake_minutes=('awake', 'sum'),
    sleep_minutes_recorded=('value', 'size'),
    sleep_logs_on_date=('logId', 'nunique'),
)
add(f, f.columns, ['sleep_minutes_recorded', 'sleep_logs_on_date'])
reconcile('sleep_minutes_recorded', len(d), absolute_tolerance=0)
for label in ['asleep', 'restless', 'awake']:
    reconcile(f'sleep_{label}_minutes', d[label].sum(), absolute_tolerance=0)

d = load('heartrate_seconds_merged.csv', 'Time')
d['_minute'] = d['_time'].dt.floor('min')
f = d.groupby(KEYS).agg(
    heart_rate_mean_bpm=('Value', 'mean'),
    heart_rate_min_bpm=('Value', 'min'),
    heart_rate_max_bpm=('Value', 'max'),
    heart_rate_readings=('Value', 'size'),
    heart_rate_minutes_recorded=('_minute', 'nunique'),
)
add(f, f.columns.difference(['heart_rate_mean_bpm']), ['heart_rate_readings', 'heart_rate_minutes_recorded'])
reconcile('heart_rate_readings', len(d), absolute_tolerance=0)
heart_control = float(d.Value.sum())

d = load('weightLogInfo_merged.csv', 'Date')
weight_counts = d.groupby(KEYS).size().rename('weight_readings')
# Select an actual last row; groupby.last() could mix non-null values from
# separate measurements and would falsely backfill missing body fat.
weight_last = d.sort_values('_time').drop_duplicates(KEYS, keep='last').set_index(KEYS)
weight_fields = {
    'WeightKg': 'weight_last_kg',
    'WeightPounds': 'weight_last_pounds',
    'BMI': 'bmi_last',
    'Fat': 'body_fat_last_percent',
    'IsManualReport': 'weight_last_is_manual',
    'LogId': 'weight_last_log_id',
    '_time': 'weight_last_logged_at',
}
f = weight_last[list(weight_fields)].rename(columns=weight_fields).join(weight_counts)
add(f, ['weight_readings'], ['weight_readings'])
reconcile('weight_readings', len(d), absolute_tolerance=0)

merged = pd.concat(frames, axis=1, join='outer').sort_index().reset_index()
assert not merged.duplicated(KEYS).any()
assert set(merged[KEYS].itertuples(index=False, name=None)) == all_source_keys
for c in coverage_columns:
    merged[c] = merged[c].fillna(0)
for c in integer_columns:
    merged[c] = merged[c].astype('Int64')
merged['has_daily_activity'] = merged.has_daily_activity.astype('boolean').fillna(False)
merged['weight_last_is_manual'] = merged.weight_last_is_manual.astype('boolean')
assert merged.participant_id.notna().all() and merged.activity_date.notna().all()
assert merged.columns.is_unique
assert all(re.fullmatch(r'[a-z][a-z0-9_]*', c) for c in merged.columns)

for column, expected, tol in controls:
    observed = float(merged[column].sum())
    assert np.isclose(observed, expected, rtol=1e-12, atol=tol), (column, observed, expected)
assert np.isclose((merged.minute_mean_mets * merged.minute_mets_minutes_recorded).sum(), mets_control)
assert np.isclose((merged.heart_rate_mean_bpm * merged.heart_rate_readings).sum(), heart_control)
assert (merged[['sleep_asleep_minutes', 'sleep_restless_minutes', 'sleep_awake_minutes']].sum(axis=1) == merged.sleep_minutes_recorded).all()
assert (merged[['minute_sedentary_minutes', 'minute_lightly_active_minutes', 'minute_fairly_active_minutes', 'minute_very_active_minutes']].sum(axis=1) == merged.minute_intensity_minutes_recorded).all()

# BigQuery-compatible ISO dates, empty CSV cells for missing measures, and
# unformatted numeric text. No timezone is invented for device-local times.
merged['activity_date'] = merged.activity_date.dt.strftime('%Y-%m-%d')
merged['weight_last_logged_at'] = merged.weight_last_logged_at.dt.strftime('%Y-%m-%d %H:%M:%S')
for c in ['has_daily_activity', 'weight_last_is_manual']:
    merged[c] = merged[c].map({True: 'true', False: 'false'}, na_action='ignore')

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
merged.to_csv(OUTPUT, index=False, na_rep='', encoding='utf-8', lineterminator='\n', float_format='%.12g')

# Reparse the produced CSV to verify the delivery, not just the in-memory frame.
with OUTPUT.open(newline='', encoding='utf-8') as handle:
    reader = csv.reader(handle)
    header = next(reader)
    csv_rows = list(reader)
assert len(csv_rows) == len(merged)
assert all(len(row) == len(header) for row in csv_rows)
roundtrip = pd.read_csv(OUTPUT, dtype={'participant_id': 'string', 'weight_last_log_id': 'string'})
assert not roundtrip.duplicated(KEYS).any()
assert roundtrip.participant_id.equals(merged.participant_id)
assert roundtrip.activity_date.tolist() == merged.activity_date.tolist()
for column, expected, tol in controls:
    assert np.isclose(roundtrip[column].sum(), expected, rtol=1e-10, atol=max(tol, 1e-6))

summary = {
    'output': str(OUTPUT),
    'rows': len(merged),
    'columns': len(merged.columns),
    'participants': int(merged.participant_id.nunique()),
    'first_date': merged.activity_date.min(),
    'last_date': merged.activity_date.max(),
    'bytes': OUTPUT.stat().st_size,
    'source_files': len(source_audit),
    'duplicate_sleep_rows_removed': source_audit['minuteSleep_merged.csv']['exact_duplicates_removed'],
    'sources': source_audit,
    'columns_in_order': merged.columns.tolist(),
    'checks': 'Passed: unique participant/date keys, all source dates retained, record counts and totals reconciled, weighted means reconciled, CSV reparse.',
    'method': 'Outer join of daily aggregates by participant_id and activity_date. Calendar-day sleep minutes. Observation-weighted heart-rate mean. Last actual weight record each day. METs divided by 10. Missing measures blank; source coverage counts zero when absent. Alternative daily/hourly/minute totals remain separate.',
}
(ROOT / 'merge_validation.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps(summary, indent=2), flush=True)
