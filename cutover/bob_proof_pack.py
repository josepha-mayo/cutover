"""Offline verification package for the existing public Bob event evidence."""
import hashlib
import io
import json
from pathlib import Path
import zipfile
from .local_starter import render_local_starter

ROOT = Path(__file__).resolve().parents[1]


def render_bob_proof_pack():
    with zipfile.ZipFile(io.BytesIO(render_local_starter())) as starter:
        files = {name: starter.read(name) for name in starter.namelist() if name != 'README.md'}
    names = [
        'cutover_task01_parcel_warehouse_repair_07a20bdb_summary.png',
        'cutover_task02_ci_review_gate_9aa1e2a2_summary.png',
        'cutover_task01_parcel_warehouse_repair_07a20bdb_history.md',
        'cutover_task02_ci_review_gate_9aa1e2a2_history.md',
        'cutover_task02_ci_review_gate_9aa1e2a2_evidence.json',
        'parcel-07a20bdb56f5-candidate.json', 'parcel-07a20bdb56f5-report.json',
        'warehouse-07a20bdb56f5-candidate.json', 'warehouse-07a20bdb56f5-report.json',
        'warehouse-07a20bdb56f5-evidence.json',
    ]
    evidence = {}
    for name in names:
        data = (ROOT/'bob_sessions'/name).read_bytes()
        if not name.endswith('.png'):
            data = data.replace(b'\r\n', b'\n')
        path = 'bob_sessions/' + name
        files[path] = data
        evidence[path] = hashlib.sha256(data).hexdigest()
    files['BOB_EVIDENCE_INVENTORY.json'] = (json.dumps(evidence, indent=2) + '\n').encode()
    files['README.md'] = b'''# Verify Cutover's actual IBM Bob contribution locally

This pack retains two existing event-period IBM Bob IDE task summaries and
histories, both saved repair plans, and their historical evidence. It does not
invoke Bob or claim a new task. The local evaluator and this packaging are Codex
work. Python 3.10+ is sufficient: no pip install, API key, account or repository
clone is needed for these commands. Inspect source before execution.

## Inspect the original event evidence

- Task 1 repair summary: [PNG](bob_sessions/cutover_task01_parcel_warehouse_repair_07a20bdb_summary.png)
- Task 1 full history, including the unsuccessful recursive-trigger attempt:
  [history](bob_sessions/cutover_task01_parcel_warehouse_repair_07a20bdb_history.md)
- Task 2 original PR gate summary: [PNG](bob_sessions/cutover_task02_ci_review_gate_9aa1e2a2_summary.png)
- Task 2 history: [history](bob_sessions/cutover_task02_ci_review_gate_9aa1e2a2_history.md)

The required PNGs are original bytes. Text files use canonical LF line endings.
BOB_EVIDENCE_INVENTORY.json records the packaged evidence hashes; it is not a
signature or independent authentication of Bob authorship.

## Freshly replay both saved repairs

Run these from the extracted folder:

```text
python -m cutover --case parcel --plan bob_sessions/parcel-07a20bdb56f5-candidate.json --bundle parcel-fresh.zip
python -m cutover.audit_bundle --bundle parcel-fresh.zip --markdown parcel-review.md
python -m cutover --contract examples/warehouse/contract.json --plan bob_sessions/warehouse-07a20bdb56f5-candidate.json --baseline-plan examples/warehouse/late_bridge.json --bundle warehouse-comparison.zip
python -m cutover.audit_bundle --bundle warehouse-comparison.zip --markdown warehouse-review.md
```

Both saved repairs should independently pass 116/116 on these fixed contracts.
The unsafe Warehouse baseline blocks 108/124. The last audit exits 1 while
writing its verified comparison because the original blocked baseline remains
in the packet. Exit 2 means unverified. Existing comparison/review files are
refused; choose new output names for another attempt.

These are fresh runs with the evaluator packaged here. Historical report files
retain their original identities and are not relabelled as runs of this version.
Different migration statement sequences have different window counts; a lower
denominator does not establish equivalent coverage. Results are bounded
sequential synthetic SQLite evidence, not production safety or adoption.

Task 2's historical GitHub controls remain at their original public source:
https://github.com/josepha-mayo/cutover/tree/main/evidence/ci_controls
This pack lets you inspect its exported IDE history; it does not rerun those
GitHub jobs or establish new IDE host acceptance. Full provenance and submitted
human-voice video/deck remain at https://cutover-rehearsal.onrender.com/proof .
'''
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return output.getvalue()
