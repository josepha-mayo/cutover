"""Generate compact, inspectable reports from every bundled SQL plan."""
import json
from pathlib import Path

from cutover.engine import load_plan, rehearse


HERE = Path(__file__).resolve().parent
CASES = ('parcel', 'contacts')
PLANS = ('rename', 'backfill', 'late_bridge', 'bridge')


def build():
    summary = []
    for case in CASES:
        for candidate in PLANS:
            report = rehearse(case, load_plan(case, candidate))
            compact = {key: value for key, value in report.items() if key != 'results'}
            compact['baseline'] = {key: report['baseline'][key] for key in ('passed', 'total')}
            compact['example_passing_migration_window'] = next(
                (result for result in report['results']
                 if result['category'] == 'migration_window' and result['passed']), None)
            (HERE / f'{case}-{candidate}.json').write_text(
                json.dumps(compact, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

            completed = [result for result in report['results']
                         if result['category'] != 'migration_window']
            windows = [result for result in report['results']
                       if result['category'] == 'migration_window']
            summary.append({
                'case': case, 'candidate': candidate,
                'baseline_passed': report['baseline']['passed'],
                'baseline_total': report['baseline']['total'],
                'completed_rollout_passed': sum(result['passed'] for result in completed),
                'completed_rollout_total': len(completed),
                'migration_windows_passed': sum(result['passed'] for result in windows),
                'migration_windows_total': len(windows),
                'passed': report['passed'], 'failed': report['failed'], 'total': report['total'],
                'plan_sha256': report['plan_hash'], 'suite_sha256': report['suite_hash'],
                'engine_sha256': report['engine_sha256'],
            })
    (HERE / 'summary.json').write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return summary


if __name__ == '__main__':
    rows = build()
    print(f'Wrote {len(rows)} compact reports and summary.json under {HERE}')
