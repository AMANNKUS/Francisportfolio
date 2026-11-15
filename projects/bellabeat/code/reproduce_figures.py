"""Reproduce Bellabeat case-study figures and numeric tables from the merged CSV."""
from pathlib import Path
import argparse
import json
from decimal import Decimal, ROUND_HALF_UP
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

def bq_round(value, digits=1):
    return float(Decimal(str(value)).quantize(Decimal(10) ** -digits, rounding=ROUND_HALF_UP))

def calculate(data):
    d = data.copy()
    d['activity_date'] = pd.to_datetime(d.activity_date)
    assert not d.duplicated(['participant_id', 'activity_date']).any()
    full = ((d.minute_steps_minutes_recorded == 1440)
            & (d.minute_calories_minutes_recorded == 1440)
            & (d.minute_intensity_minutes_recorded == 1440))
    a = d.loc[full].copy()
    a['recorded_active_minutes'] = (a.minute_lightly_active_minutes
        + a.minute_fairly_active_minutes + a.minute_very_active_minutes)
    a['fairly_or_very_active_minutes'] = a.minute_fairly_active_minutes + a.minute_very_active_minutes
    a['weekday_order'] = a.activity_date.dt.weekday + 1
    a['weekday'] = a.activity_date.dt.day_name()
    a['is_weekend'] = a.activity_date.dt.weekday >= 5
    pos = a[a.minute_total_steps > 0]
    u = a.groupby('participant_id').agg(
        recorded_days=('participant_id', 'size'),
        zero_step_days=('minute_total_steps', lambda x: int((x == 0).sum())),
        mean_daily_steps=('minute_total_steps', 'mean'),
        mean_daily_calories_kcal=('minute_total_calories_kcal', 'mean'),
        mean_active_minutes=('recorded_active_minutes', 'mean'),
        mean_fairly_or_very_active_minutes=('fairly_or_very_active_minutes', 'mean'))
    uw = a.groupby(['participant_id', 'weekday_order', 'weekday']).agg(
        recorded_days=('participant_id', 'size'),
        mean_steps=('minute_total_steps', 'mean'),
        mean_active_minutes=('recorded_active_minutes', 'mean'),
        mean_fairly_or_very_active_minutes=('fairly_or_very_active_minutes', 'mean'))
    weekday = uw.groupby(['weekday_order', 'weekday']).agg(
        distinct_participant_ids=('recorded_days', 'size'),
        participant_days=('recorded_days', 'sum'),
        equal_id_weighted_mean_steps=('mean_steps', 'mean'),
        equal_id_weighted_mean_active_minutes=('mean_active_minutes', 'mean'),
        equal_id_weighted_mean_fairly_or_very_active_minutes=('mean_fairly_or_very_active_minutes', 'mean')).reset_index()
    week = a.groupby(['participant_id', 'is_weekend']).minute_total_steps.mean().unstack().dropna()
    sensitivity = []
    for label, frame in [('All full-coverage days', a), ('Positive-step full-coverage days', pos)]:
        sensitivity.append({'sample': label, 'participant_days': len(frame),
            'distinct_participant_ids': frame.participant_id.nunique(),
            'zero_step_days': int((frame.minute_total_steps == 0).sum()),
            'mean_daily_steps': frame.minute_total_steps.mean(),
            'mean_daily_calories_kcal': frame.minute_total_calories_kcal.mean(),
            'mean_recorded_active_minutes': frame.recorded_active_minutes.mean(),
            'mean_fairly_or_very_active_minutes': frame.fairly_or_very_active_minutes.mean(),
            'step_calorie_correlation': frame.minute_total_steps.corr(frame.minute_total_calories_kcal)})
    sensitivity = pd.DataFrame(sensitivity)
    s = d[d.sleep_minutes_recorded > 0].copy()
    su = s.groupby('participant_id').agg(recorded_sleep_days=('participant_id', 'size'),
        mean_recorded_asleep_minutes=('sleep_asleep_minutes', 'mean'),
        mean_recorded_restless_minutes=('sleep_restless_minutes', 'mean'),
        mean_recorded_awake_minutes=('sleep_awake_minutes', 'mean'))
    sleep_weighting = pd.DataFrame([
        {'weighting_method': 'Daily-record weighted', 'participant_days': len(s),
         'distinct_participant_ids': s.participant_id.nunique(),
         'mean_recorded_asleep_minutes': s.sleep_asleep_minutes.mean()},
        {'weighting_method': 'Equal-ID weighted', 'participant_days': len(s),
         'distinct_participant_ids': len(su),
         'mean_recorded_asleep_minutes': su.mean_recorded_asleep_minutes.mean()}])
    sleep_weighting['mean_recorded_asleep_hours'] = sleep_weighting.mean_recorded_asleep_minutes / 60
    coverage = []
    for name, frame in [('All available days', d), ('Full activity-coverage days', a)]:
        has = frame.sleep_minutes_recorded > 0
        coverage.append({'cohort': name, 'available_participant_days': len(frame),
            'distinct_participant_ids': frame.participant_id.nunique(),
            'days_with_sleep_records': int(has.sum()),
            'ids_with_sleep_records': frame.loc[has, 'participant_id'].nunique(),
            'percentage_of_available_days_with_sleep_records': 100 * has.mean()})
    availability = []
    for name, frame in [('Positive-step days', pos), ('Zero-step days', a[a.minute_total_steps == 0])]:
        has = frame.sleep_minutes_recorded > 0
        availability.append({'step_record_group': name, 'participant_days': len(frame),
            'distinct_participant_ids': frame.participant_id.nunique(),
            'days_with_sleep_records': int(has.sum()),
            'ids_with_sleep_records': frame.loc[has, 'participant_id'].nunique(),
            'percentage_of_days_with_sleep_records': 100 * has.mean()})
    availability = pd.DataFrame(availability)
    joint = a[a.sleep_minutes_recorded > 0]
    joint_stats = []
    for name, frame in [('All matched full-coverage days', joint),
                        ('Positive-step matched full-coverage days', joint[joint.minute_total_steps > 0])]:
        joint_stats.append({'sample': name, 'matched_participant_days': len(frame),
            'distinct_participant_ids': frame.participant_id.nunique(),
            'mean_daily_steps': frame.minute_total_steps.mean(),
            'mean_recorded_asleep_minutes': frame.sleep_asleep_minutes.mean(),
            'same_day_step_sleep_correlation': frame.minute_total_steps.corr(frame.sleep_asleep_minutes)})
    summary = {'all_rows': len(d), 'all_ids': int(d.participant_id.nunique()),
        'activity_rows': len(a), 'activity_ids': int(a.participant_id.nunique()),
        'activity_first_date': str(a.activity_date.min().date()),
        'activity_last_date': str(a.activity_date.max().date()),
        'mean_steps_per_day': float(a.minute_total_steps.mean()),
        'median_steps_per_day': float(a.minute_total_steps.median()),
        'equal_id_mean_steps': float(u.mean_daily_steps.mean()),
        'mean_active_minutes': float(a.recorded_active_minutes.mean()),
        'mean_light_minutes': float(a.minute_lightly_active_minutes.mean()),
        'mean_fairly_or_very_minutes': float(a.fairly_or_very_active_minutes.mean()),
        'light_share_of_active_minutes_pct': float(100 * a.minute_lightly_active_minutes.sum() / a.recorded_active_minutes.sum()),
        'zero_step_days': int((a.minute_total_steps == 0).sum()),
        'zero_step_pct': float(100 * (a.minute_total_steps == 0).mean()),
        'weekday_mean_steps': float(week[False].mean()),
        'weekend_mean_steps': float(week[True].mean()),
        'weekend_minus_weekday_steps': float((week[True] - week[False]).mean()),
        'sleep_rows': len(s), 'sleep_ids': int(s.participant_id.nunique()),
        'matched_sleep_rows': len(joint), 'matched_sleep_ids': int(joint.participant_id.nunique()),
        'sleep_days_min': int(su.recorded_sleep_days.min()), 'sleep_days_max': int(su.recorded_sleep_days.max()),
        'ids_with_1_to_4_sleep_days': int((su.recorded_sleep_days <= 4).sum())}
    # Controls are the results verified in BigQuery during the case study.
    assert (len(d), len(a), len(pos), len(s), len(joint)) == (1060, 988, 818, 467, 447)
    assert (int(d.participant_id.nunique()), len(u), len(su)) == (35, 33, 23)
    assert bq_round(a.minute_total_steps.mean()) == 6889.7
    assert bq_round(u.mean_daily_steps.mean()) == 6836.3
    assert bq_round(pos.minute_total_steps.mean()) == 8321.5
    assert [bq_round(v) for v in weekday.equal_id_weighted_mean_steps] == [6563.9, 6798.1, 7132.5, 7043.1, 6832.2, 6956.3, 6574.6]
    assert [bq_round(v, 3) for v in sensitivity.step_calorie_correlation] == [0.650, 0.556]
    assert [bq_round(v) for v in sleep_weighting.mean_recorded_asleep_minutes] == [391.9, 359.2]
    assert [bq_round(v, 3) for v in pd.DataFrame(joint_stats).same_day_step_sleep_correlation] == [-0.113, -0.104]
    assert [bq_round(v) for v in availability.percentage_of_days_with_sleep_records] == [54.5, 0.6]
    return summary, {'weekday_summary': weekday, 'activity_profiles': u.reset_index(),
        'zero_step_sensitivity': sensitivity, 'sleep_coverage': pd.DataFrame(coverage),
        'sleep_weighting': sleep_weighting, 'sleep_profiles': su.reset_index(),
        'same_day_activity_sleep': pd.DataFrame(joint_stats), 'sleep_availability_by_steps': availability}

def figures(summary, tables, out):
    out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
        'axes.titlesize': 14, 'axes.titleweight': 'bold', 'axes.labelsize': 10.5,
        'axes.spines.top': False, 'axes.spines.right': False, 'axes.spines.left': False,
        'axes.edgecolor': '#B8C2CA', 'axes.labelcolor': '#26343F',
        'xtick.color': '#44525C', 'ytick.color': '#26343F',
        'svg.fonttype': 'none', 'savefig.facecolor': 'white'})
    teal, blue, gray = '#316D73', '#335A80', '#8B969E'
    def save(fig, name):
        fig.savefig(out / (name + '.png'), dpi=300)
        fig.savefig(out / (name + '.svg'))
        plt.close(fig)
    def base(height):
        fig, ax = plt.subplots(figsize=(8.0, height))
        ax.set_axisbelow(True)
        ax.xaxis.grid(True, color='#E6EBEE', linewidth=.7)
        ax.tick_params(axis='y', length=0, pad=8)
        return fig, ax
    w = tables['weekday_summary']
    fig, ax = base(3.9)
    ax.barh(w.weekday, w.equal_id_weighted_mean_steps, color=teal, height=.66)
    ax.invert_yaxis(); ax.set_xlim(0, 8500)
    for y, value in enumerate(w.equal_id_weighted_mean_steps):
        ax.text(value + 105, y, f'{value:,.0f}', va='center', fontsize=10.5)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p: f'{v:,.0f}'))
    ax.set_xlabel('Mean daily steps with each ID given equal weight')
    ax.set_title('Average recorded steps by weekday', loc='left', pad=14)
    fig.subplots_adjust(left=.17, right=.97, top=.83, bottom=.20)
    fig.text(.17, .035, '33 IDs. Complete minute-record coverage for steps, calories and intensity.', fontsize=9, color='#56626B')
    save(fig, '01_weekday_steps')
    t = tables['zero_step_sensitivity']
    fig, ax = base(2.9)
    labels = ['All full-coverage days\n988 days, 33 IDs', 'Positive-step days\n818 days, 33 IDs']
    ax.barh(labels, t.mean_daily_steps, color=[teal, blue], height=.53)
    ax.invert_yaxis(); ax.set_xlim(0, 10500)
    for y, value in enumerate(t.mean_daily_steps):
        ax.text(value + 140, y, f'{value:,.1f}', va='center', fontsize=11)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p: f'{v:,.0f}'))
    ax.set_xlabel('Mean steps per recorded day')
    ax.set_title('Zero-step records affect the daily average', loc='left', pad=14)
    fig.subplots_adjust(left=.29, right=.98, top=.75, bottom=.30)
    fig.text(.29, .03, 'Each day has equal weight. The positive-step row is a sensitivity estimate.', fontsize=8.8, color='#56626B')
    save(fig, '02_zero_step_sensitivity')
    t = tables['sleep_availability_by_steps']
    fig, ax = base(2.9)
    labels = ['Positive-step days', 'Zero-step days']
    vals = t.percentage_of_days_with_sleep_records
    ax.barh(labels, vals, color=[teal, gray], height=.53)
    ax.invert_yaxis(); ax.set_xlim(0, 100)
    for y, row in t.iterrows():
        label = f'{row.percentage_of_days_with_sleep_records:.1f}% ({row.days_with_sleep_records}/{row.participant_days} days)'
        ax.text(row.percentage_of_days_with_sleep_records + 1.8, y, label, va='center', fontsize=10)
    ax.set_xlabel('Percentage of days with available sleep records')
    ax.set_title('Sleep-data availability differs by step status', loc='left', pad=14)
    fig.subplots_adjust(left=.27, right=.98, top=.75, bottom=.30)
    fig.text(.27, .03, 'Full activity-coverage sample. An ID may contribute days to both groups.', fontsize=8.8, color='#56626B')
    save(fig, '03_sleep_availability')
    t = tables['sleep_weighting']
    fig, ax = base(2.9)
    labels = ['Each day has equal weight', 'Each ID has equal weight']
    ax.barh(labels, t.mean_recorded_asleep_hours, color=[teal, blue], height=.53)
    ax.invert_yaxis(); ax.set_xlim(0, 9)
    for y, value in enumerate(t.mean_recorded_asleep_hours):
        ax.text(value + .13, y, f'{value:.2f}', va='center', fontsize=11)
    ax.set_xlabel('Recorded asleep hours per observed calendar day')
    ax.set_title('Averaging method changes the sleep estimate', loc='left', pad=14)
    fig.subplots_adjust(left=.34, right=.98, top=.75, bottom=.30)
    fig.text(.34, .03, '467 days from 23 IDs. Calendar-day totals do not measure complete nights.', fontsize=8.6, color='#56626B')
    save(fig, '04_sleep_weighting')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data/Fitbit_Daily_Merged.csv'))
    parser.add_argument('--output-dir', type=Path, default=Path('charts'))
    parser.add_argument('--results-dir', type=Path, default=Path('results'))
    args = parser.parse_args()
    summary, tables = calculate(pd.read_csv(args.data))
    args.results_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        frame.to_csv(args.results_dir / (name + '.csv'), index=False, float_format='%.12g')
    (args.results_dir / 'summary.json').write_text(json.dumps(summary, indent=2))
    figures(summary, tables, args.output_dir)
    print(json.dumps({'charts': 4, 'tables': len(tables), 'validation': 'Matched the verified BigQuery results.'}))

if __name__ == '__main__':
    main()
