"""Verify the public warehouse demo against this checkout and rerun its witness.

Run: python -m evidence.verify_hosted
This is pre-event deterministic verification, not IBM Bob task evidence.
"""

import json
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from cutover.reporting import render_reproduction
from cutover.service import verify_report_against_replay


ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE = ROOT / 'examples' / 'warehouse'
URL = 'https://cutover-rehearsal.onrender.com/api/rehearse'
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


def main():
    contract = json.loads((WAREHOUSE / 'contract.json').read_text(encoding='utf-8'))
    plan = json.loads((WAREHOUSE / 'late_bridge.json').read_text(encoding='utf-8'))
    request = urllib.request.Request(
        URL,
        data=json.dumps({'case': 'custom', 'contract': contract, 'plan': plan}).encode(),
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError('Hosted evidence exceeded the 8 MiB verification limit')
    report = json.loads(raw)
    if (report.get('status'), report.get('passed'), report.get('total')) != ('blocked', 108, 124):
        raise ValueError('The hosted warehouse result differs from the documented 108/124 witness')

    verify_report_against_replay('custom', plan, report, contract)
    reproduction = render_reproduction(report, contract)
    if report.get('reproduction_python') != reproduction:
        raise ValueError('The hosted standalone witness differs from the local renderer')
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / 'witness.py'
        path.write_text(reproduction, encoding='utf-8')
        executed = subprocess.run(
            [sys.executable, '-I', str(path)], cwd=folder,
            capture_output=True, text=True, encoding='utf-8', timeout=15,
        )
        if executed.returncode:
            raise ValueError(f'Standalone witness failed: {executed.stderr.strip()}')
        outcome = json.loads(executed.stdout)
    if (outcome.get('status'), outcome.get('probe'),
            outcome.get('expected', {}).get('11'), outcome.get('actual', {}).get('11')) != (
            'REPRODUCED', report['witness']['id'], 'R-07', 'A-01'):
        raise ValueError('Standalone witness did not reproduce the hosted data gap')
    print(f"PASS: hosted engine {report['engine_version']}, warehouse {report['passed']}/{report['total']}, "
          f"independent replay and standalone witness {outcome['probe']}")


if __name__ == '__main__':
    main()
