"""Recompute the curated detection ablation from executable SQL rehearsals."""
import json
from pathlib import Path

from cutover.engine import load_plan, rehearse


HERE = Path(__file__).resolve().parent
CASES = ('parcel', 'contacts')
UNSAFE = ('rename', 'backfill', 'late_bridge')
PLANS = (*UNSAFE, 'bridge')


def evaluate():
    rows = []
    for case in CASES:
        for name in PLANS:
            report = rehearse(case, load_plan(case, name))
            completed = [r for r in report['results'] if r['category'] != 'migration_window']
            windows = [r for r in report['results'] if r['category'] == 'migration_window']
            rows.append({
                'case': case,
                'candidate': name,
                'intentionally_unsafe': name in UNSAFE,
                'baseline': {'passed': report['baseline']['passed'], 'total': report['baseline']['total']},
                'completed_rollout': {'passed': sum(r['passed'] for r in completed), 'total': len(completed)},
                'migration_windows': {'passed': sum(r['passed'] for r in windows), 'total': len(windows)},
                'plan_sha256': report['plan_hash'],
                'contract_sha256': report['contract_hash'],
                'suite_sha256': report['suite_hash'],
                'engine_sha256': report['engine_sha256'],
            })

    stage_detections = {}
    for stage in ('baseline', 'completed_rollout', 'full_suite'):
        stage_detections[stage] = {}
        for case in CASES:
            subset = [r for r in rows if r['case'] == case and r['intentionally_unsafe']]
            if stage == 'baseline':
                detected = [r['candidate'] for r in subset if r['baseline']['passed'] < r['baseline']['total']]
            elif stage == 'completed_rollout':
                detected = [r['candidate'] for r in subset if r['completed_rollout']['passed'] < r['completed_rollout']['total']]
            else:
                detected = [r['candidate'] for r in subset if
                            r['completed_rollout']['passed'] < r['completed_rollout']['total'] or
                            r['migration_windows']['passed'] < r['migration_windows']['total']]
            stage_detections[stage][case] = {'detected': detected, 'out_of': len(subset)}

    # Make the narrative fail closed if the underlying fixture behavior changes.
    for case in CASES:
        assert stage_detections['baseline'][case]['detected'] == []
        assert stage_detections['completed_rollout'][case]['detected'] == ['rename', 'backfill']
        assert stage_detections['full_suite'][case]['detected'] == list(UNSAFE)
        safe = next(r for r in rows if r['case'] == case and r['candidate'] == 'bridge')
        assert safe['baseline'] == {'passed': 8, 'total': 8}
        assert safe['completed_rollout'] == {'passed': 76, 'total': 76}
        assert safe['migration_windows'] == {'passed': 48, 'total': 48}

    return {
        'description': 'Controlled ablation on three deliberately unsafe rollout patterns and one passing reference, repeated on two structurally similar SQLite sample contracts.',
        'interpretation_limit': 'These are curated fixtures, not independent production incidents, customer productivity measurements, or a general defect-recall estimate.',
        'rows': rows,
        'unsafe_pattern_detection': stage_detections,
    }


if __name__ == '__main__':
    output = HERE / 'ablation.json'
    output.write_text(json.dumps(evaluate(), indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(output)
