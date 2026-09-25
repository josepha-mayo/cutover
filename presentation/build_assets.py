"""Create the hackathon cover and either a clearly marked draft or an evidenced deck."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from cutover.service import run_rehearsal, verify_report_against_replay

FONTS = Path('C:/Windows/Fonts')
INK = '#18251f'
PANEL = '#25372c'
CREAM = '#f5f5ed'
MUTED = '#aebdac'
ORANGE = '#ee683f'
LIME = '#b9d38d'
RED = '#e79278'


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def cover():
    image = Image.new('RGB', (1920, 1080), INK)
    draw = ImageDraw.Draw(image)
    for x in range(0, 1920, 80):
        draw.line((x, 0, x, 1080), fill='#1d2c24', width=1)
    for y in range(0, 1080, 80):
        draw.line((0, y, 1920, y), fill='#1d2c24', width=1)

    draw.line((117, 117, 148, 85), fill=ORANGE, width=8)
    draw.polygon([(129, 81), (154, 79), (151, 104)], fill=ORANGE)
    draw.text((166, 73), 'cutover', font=font('segoeuib.ttf', 43), fill=CREAM)
    draw.ellipse((332, 111, 341, 120), fill=ORANGE)
    draw.text((1510, 86), 'IBM BOB 2.0 HACKATHON', font=font('consolab.ttf', 22), fill=MUTED)
    draw.line((112, 157, 1808, 157), fill='#405044', width=2)

    draw.rectangle((112, 250, 122, 265), fill=ORANGE)
    draw.text((143, 246), 'RELEASE ENGINEERING / EXECUTABLE EVIDENCE',
              font=font('consolab.ttf', 22), fill=LIME)
    draw.text((106, 300), 'A green build.', font=font('segoeuib.ttf', 93), fill=CREAM)
    draw.text((106, 406), 'A broken', font=font('segoeuib.ttf', 93), fill=CREAM)
    draw.text((106, 512), 'handover.', font=font('segoeuib.ttf', 93), fill=ORANGE)
    draw.text((113, 667), 'Old code and new code share one database.',
              font=font('segoeui.ttf', 31), fill='#dae4d5')
    draw.text((113, 710), 'Cutover rehearses the writes between migration steps.',
              font=font('segoeui.ttf', 31), fill='#dae4d5')

    draw.rounded_rectangle((1120, 239, 1808, 814), radius=23, fill=PANEL, outline='#516452', width=2)
    draw.text((1162, 274), 'THE MISSED WINDOW', font=font('consolab.ttf', 26), fill=LIME)
    draw.line((1198, 356, 1198, 745), fill='#82967b', width=5)
    rows = [
        (362, '01', 'ADD COLUMN', 'Both versions can still write.'),
        (472, '02', 'BACKFILL', 'Existing rows are copied.'),
        (582, '!', 'OLD WORKER WRITES', 'New column stays stale.'),
        (692, '03', 'ADD SYNC', 'Protection arrives too late.'),
    ]
    for y, n, title, subtitle in rows:
        danger = n == '!'
        if danger:
            draw.rounded_rectangle((1142, y - 17, 1778, y + 83), radius=12,
                                   fill='#553c33', outline=ORANGE, width=2)
        draw.ellipse((1179, y + 6, 1217, y + 44), fill=ORANGE if danger else LIME)
        draw.text((1188 if n != '!' else 1191, y + 9), n,
                  font=font('consolab.ttf', 23), fill=INK)
        draw.text((1245, y), title, font=font('consolab.ttf', 24), fill=CREAM)
        draw.text((1245, y + 39), subtitle, font=font('segoeui.ttf', 21), fill=RED if danger else MUTED)

    draw.line((112, 839, 1808, 839), fill='#405044', width=2)
    draw.text((112, 878), '76/76', font=font('consolab.ttf', 64), fill=LIME)
    draw.text((112, 965), 'completed-rollout probes pass', font=font('segoeui.ttf', 24), fill=MUTED)
    draw.text((948, 878), '16', font=font('consolab.ttf', 64), fill=ORANGE)
    draw.text((948, 965), 'migration-window probes fail', font=font('segoeui.ttf', 24), fill=MUTED)
    draw.text((1660, 968), 'v0.3 / SQLITE', font=font('consola.ttf', 17), fill=MUTED)
    image.save(HERE / 'cover.png', optimize=True)


def register_fonts():
    pdfmetrics.registerFont(TTFont('Segoe', str(FONTS / 'segoeui.ttf')))
    pdfmetrics.registerFont(TTFont('SegoeBold', str(FONTS / 'segoeuib.ttf')))
    pdfmetrics.registerFont(TTFont('Consolas', str(FONTS / 'consola.ttf')))
    pdfmetrics.registerFont(TTFont('ConsolasBold', str(FONTS / 'consolab.ttf')))


W, H = 960, 540


def text(c, x, y, value, size=18, color=CREAM, face='Segoe'):
    c.setFillColor(HexColor(color))
    c.setFont(face, size)
    c.drawString(x, y, value)


def box(c, x, y, w, h, fill=PANEL, stroke=None, radius=12):
    c.setFillColor(HexColor(fill))
    c.setStrokeColor(HexColor(stroke or fill))
    c.roundRect(x, y, w, h, radius, fill=1, stroke=bool(stroke))


def base(c, number, title, kicker, final=False):
    c.setFillColor(HexColor(INK))
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(HexColor(ORANGE))
    c.rect(45, 505, 9, 9, fill=1, stroke=0)
    text(c, 63, 502, 'cutover.', 19, CREAM, 'SegoeBold')
    text(c, 666, 506, 'IBM BOB 2.0  /  SUBMISSION' if final else 'IBM BOB 2.0  /  DRAFT',
         10, MUTED, 'Consolas')
    c.setStrokeColor(HexColor('#415246'))
    c.line(45, 485, 915, 485)
    text(c, 45, 451, kicker, 11, LIME, 'ConsolasBold')
    text(c, 45, 402, title, 34, CREAM, 'SegoeBold')
    c.line(45, 38, 915, 38)
    text(c, 45, 21, 'Bounded SQLite rehearsal; no production safety claim.' if final else
         'Pre-event draft. Bob session evidence still required.', 9, MUTED, 'Consolas')
    text(c, 883, 21, f'{number:02d}', 10, MUTED, 'Consolas')


def event_evidence(path):
    """Require observed Bob artifacts; this is a consistency check, not authorship proof."""
    evidence = json.loads(Path(path).read_text(encoding='utf-8'))
    required = ('bob_task_id', 'bob_summary_image', 'bob_contribution', 'session_time_utc')
    if any(not isinstance(evidence.get(key), str) or not evidence[key].strip() for key in required):
        raise ValueError('Bob evidence must name a real task, screenshot, contribution and time')
    if not re.fullmatch(r'[0-9a-f]{32}', evidence['bob_task_id']):
        raise ValueError('Bob evidence needs the full IDE task ID')
    has_candidate = bool(evidence.get('bob_candidate'))
    has_report = bool(evidence.get('candidate_report'))
    if has_candidate != has_report:
        raise ValueError('A Bob candidate and its executed report must appear together')
    if not has_candidate and not evidence.get('ci_evidence'):
        raise ValueError('Without a saved Bob candidate, a verified Bob-built CI gate is required')
    session_time = parse_time(evidence['session_time_utc'], 'session_time_utc')
    if not (datetime(2026, 9, 25, 15, tzinfo=timezone.utc) <= session_time <=
            datetime(2026, 9, 27, 15, tzinfo=timezone.utc)):
        raise ValueError('Bob session time must fall within the advertised hackathon window')
    paths = ('bob_summary_image', 'bob_candidate', 'candidate_report') if has_candidate else ('bob_summary_image',)
    for key in paths:
        file = (ROOT / evidence[key]).resolve()
        if not file.is_relative_to(ROOT) or not file.is_file():
            raise ValueError(f'{key} must be an existing project file')
        evidence[key] = file
    if (not evidence['bob_summary_image'].is_relative_to(ROOT / 'bob_sessions') or
            evidence['bob_task_id'][:8] not in evidence['bob_summary_image'].name):
        raise ValueError('Bob repair summary must be a staged PNG for its IDE task')
    with Image.open(evidence['bob_summary_image']) as screenshot:
        if screenshot.format != 'PNG':
            raise ValueError('Bob repair task summary must be PNG')
        screenshot.verify()
    if not has_candidate:
        records = [json.loads(record.read_text(encoding='utf-8')) for record in
                   (ROOT / 'bob_sessions').glob('*_evidence.json')]
        if not any(record.get('bob_task_id') == evidence['bob_task_id'] and
                   record.get('ide_summary') ==
                   evidence['bob_summary_image'].relative_to(ROOT).as_posix() and
                   record.get('ide_summary_sha256') ==
                   hashlib.sha256(evidence['bob_summary_image'].read_bytes()).hexdigest()
                   for record in records):
            raise ValueError('Unresolved Bob repair needs a staged IDE task record')
    if has_candidate:
        plan = json.loads(evidence['bob_candidate'].read_text(encoding='utf-8'))
        report = json.loads(evidence['candidate_report'].read_text(encoding='utf-8'))
        if report.get('plan') != plan or report.get('status') not in ('pass', 'blocked'):
            raise ValueError('Candidate report must be an executed verdict for the named Bob candidate')
        if report.get('case') != 'parcel':
            raise ValueError('This deck currently describes the Parcel sample')
        results = report.get('results')
        if not isinstance(results, list):
            raise ValueError('Candidate report must be the full CLI report with executed probe results')
        if (report.get('total') != len(results) or
                report.get('passed') != sum(result.get('passed') is True for result in results) or
                report.get('failed') != sum(result.get('passed') is False for result in results) or
                (report['status'] == 'pass') != (report['failed'] == 0)):
            raise ValueError('Candidate report verdict and probe counts disagree')
        report_time = parse_time(report.get('created_at'), 'report.created_at')
        if not session_time <= report_time <= datetime(2026, 9, 27, 15, tzinfo=timezone.utc):
            raise ValueError('Candidate report must be generated after the Bob task and before submission close')
        plan_hash = hashlib.sha256(json.dumps(plan, ensure_ascii=False, sort_keys=True,
                                              separators=(',', ':')).encode()).hexdigest()
        engine_source = (ROOT / 'cutover' / 'engine.py').read_bytes().replace(b'\r\n', b'\n')
        engine_hash = hashlib.sha256(engine_source).hexdigest()
        if report.get('plan_hash') != plan_hash or report.get('engine_sha256') != engine_hash:
            raise ValueError('Candidate report must match the current plan and evaluator source')
        verify_report_against_replay('parcel', plan, report)
        evidence['report'] = report
    if evidence.get('ci_evidence'):
        evidence['ci_evidence'] = verified_ci_evidence(evidence['ci_evidence'], Path(path).parent)
    return evidence


def verified_ci_evidence(source, manifest_dir):
    """Accept a CI slide only with three independently replayed PR-run receipts."""
    if not isinstance(source, dict):
        raise ValueError('CI evidence must be an object')
    task_id = source.get('bob_ci_task_id')
    if not isinstance(task_id, str) or not re.fullmatch(r'[0-9a-f]{32}', task_id):
        raise ValueError('CI evidence needs the full Bob IDE task ID')
    image_name = source.get('bob_ci_summary_image')
    if not isinstance(image_name, str):
        raise ValueError('CI evidence needs Bob task summary image')
    image = (ROOT / image_name).resolve()
    if (not image.is_relative_to(ROOT / 'bob_sessions') or not image.is_file() or
            task_id[:8] not in image.name):
        raise ValueError('CI summary must be a staged Bob PNG named for this task')
    with Image.open(image) as screenshot:
        if screenshot.format != 'PNG':
            raise ValueError('CI task summary must be a PNG')
        screenshot.verify()
    task_records = []
    for record_path in (ROOT / 'bob_sessions').glob('*_evidence.json'):
        record = json.loads(record_path.read_text(encoding='utf-8'))
        if record.get('bob_task_id') == task_id:
            task_records.append(record)
    if (len(task_records) != 1 or
            task_records[0].get('ide_summary') != image.relative_to(ROOT).as_posix() or
            task_records[0].get('ide_summary_sha256') !=
            hashlib.sha256(image.read_bytes()).hexdigest()):
        raise ValueError('CI Bob task summary has no matching staged IDE task record')
    if task_id not in (ROOT / 'docs/PROVENANCE.md').read_text(encoding='utf-8'):
        raise ValueError('CI Bob task ID is missing from public provenance')
    if not (ROOT / '.github/workflows/cutover-review.yml').is_file():
        raise ValueError('Verified CI slide requires the saved Cutover PR workflow')

    receipt_names = source.get('run_receipts')
    expected = {
        'unsafe': ('blocked', 108, 124, 'window_write_after_2-0', 'failure', 1),
        'safe_reference': ('pass', 124, 124, None, 'success', 0),
        'regressed': ('blocked', 100, 116, 'new_to_old-0', 'failure', 1),
    }
    if not isinstance(receipt_names, dict) or set(receipt_names) != set(expected):
        raise ValueError('CI slide requires unsafe, safe_reference and regressed run receipts')
    contract = json.loads((ROOT / 'examples/warehouse/contract.json').read_text(encoding='utf-8'))
    runs = {}
    seen = set()
    for control, (status, passed, total, witness, conclusion, audit_exit) in expected.items():
        name = receipt_names[control]
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f'{control} run receipt path is missing')
        receipt_path = Path(name)
        if not receipt_path.is_absolute():
            receipt_path = manifest_dir / receipt_path
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        run_id = receipt.get('run')
        started = parse_time(receipt.get('created_at_utc'), f'{control} run start')
        finished = parse_time(receipt.get('updated_at_utc'), f'{control} run finish')
        if not (datetime(2026, 9, 25, 15, tzinfo=timezone.utc) <=
                started <= finished < datetime(2026, 9, 27, 15, tzinfo=timezone.utc)):
            raise ValueError(f'{control} PR run falls outside the event build window')
        if (type(run_id) is not int or run_id <= 0 or run_id in seen or
                receipt.get('url') != f'https://github.com/josepha-mayo/cutover/actions/runs/{run_id}' or
                receipt.get('workflow_path', '').split('@', 1)[0] != '.github/workflows/cutover-review.yml' or
                receipt.get('conclusion') != conclusion or receipt.get('status') != status or
                receipt.get('passed') != passed or receipt.get('total') != total or
                receipt.get('first_witness') != witness or
                receipt.get('independent_audit_exit') != audit_exit or
                receipt.get('matching_markdown_artifacts', 0) < 1 or
                receipt.get('matching_zip_artifacts') != 1 or
                receipt.get('downloaded_summary_verified') is not True or
                receipt.get('downloaded_verdict_verified') is not True or
                not re.fullmatch(r'[0-9a-f]{40}', str(receipt.get('head_sha', '')))):
            raise ValueError(f'{control} receipt is not a verified Cutover PR run')
        report_path = Path(receipt['report'])
        report = json.loads(report_path.read_text(encoding='utf-8'))
        report_time = parse_time(report.get('created_at'), f'{control} report time')
        if not started <= report_time <= finished:
            raise ValueError(f'{control} report falls outside its GitHub run')
        plan = json.loads((ROOT / 'work/ci-controls-20260924' / f'{control}.json').read_text(encoding='utf-8'))
        # Git stores these Windows text fixtures with LF while the local
        # checkout can have CRLF. Bind the receipt to the exact Git blob.
        checked_in_hash = hashlib.sha256(
            (ROOT / 'work/ci-controls-20260924' / f'{control}.json')
            .read_bytes().replace(b'\r\n', b'\n')
        ).hexdigest()
        if (receipt.get('checked_in_candidate_sha256') != checked_in_hash or
                not re.fullmatch(r'[0-9a-f]{40}', str(
                    receipt.get('checked_in_candidate_git_blob_sha', '')))):
            raise ValueError(f'{control} receipt does not bind its PR head to the checked-in candidate')
        actual_witness = report.get('witness')
        actual_witness = actual_witness.get('id') if isinstance(actual_witness, dict) else None
        if (report.get('case') != 'custom' or report.get('plan') != plan or
                (report.get('status'), report.get('passed'), report.get('total')) !=
                (status, passed, total) or
                actual_witness != witness):
            raise ValueError(f'{control} downloaded report disagrees with the receipt')
        verify_report_against_replay('custom', plan, report, contract)
        live = subprocess.run(
            ['gh', 'run', 'view', str(run_id), '--json',
             'status,conclusion,url,headSha,createdAt,updatedAt'],
            cwd=ROOT, text=True, capture_output=True, timeout=30, check=False,
        )
        if live.returncode != 0:
            raise ValueError(f'Cannot confirm {control} GitHub run: {live.stderr[:180]}')
        current = json.loads(live.stdout)
        if (current.get('status') != 'completed' or current.get('conclusion') != conclusion or
                current.get('url') != receipt['url'] or
                current.get('headSha') != receipt['head_sha'] or
                current.get('createdAt') != receipt['created_at_utc'] or
                current.get('updatedAt') != receipt['updated_at_utc']):
            raise ValueError(f'{control} GitHub run no longer matches its receipt')
        seen.add(run_id)
        runs[control] = receipt
    return {'bob_ci_task_id': task_id, 'bob_ci_summary_image': image, 'runs': runs}


def parse_time(value, label):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (TypeError, AttributeError, ValueError) as exc:
        raise ValueError(f'{label} must be an ISO-8601 timestamp') from exc
    if parsed.tzinfo is None:
        raise ValueError(f'{label} must include a timezone')
    return parsed.astimezone(timezone.utc)


def bob_slide(c, evidence):
    report = evidence.get('report')
    passing = report is not None and report['status'] == 'pass'
    title = ('Bob repaired the missed window.' if passing else
             'Bob exposed a remaining gap.' if report else
             'Bob session: repair remains open.')
    base(c, 7, title, '06  /  OBSERVED IBM BOB WORK', final=True)
    box(c, 45, 94, 506, 286, PANEL, '#516452')
    with Image.open(evidence['bob_summary_image']) as screenshot:
        width, height = screenshot.size
    scale = min(478 / width, 248 / height)
    drawn_w, drawn_h = width * scale, height * scale
    c.drawImage(str(evidence['bob_summary_image']), 59 + (478 - drawn_w) / 2,
                108 + (248 - drawn_h) / 2, width=drawn_w, height=drawn_h)
    text(c, 59, 372, 'ACTUAL BOB TASK SUMMARY', 11, LIME, 'ConsolasBold')
    box(c, 573, 94, 342, 286)
    text(c, 591, 344, f"Task: {evidence['bob_task_id'][:33]}", 12, CREAM, 'Consolas')
    if report:
        text(c, 591, 315, f"Candidate: {plan_label(report['plan'])}", 12, CREAM, 'Consolas')
        text(c, 591, 277, f"Verdict: {report['passed']}/{report['total']} probes", 17,
             LIME if passing else ORANGE, 'ConsolasBold')
        windows = next((item for item in report['categories'] if item['id'] == 'migration_window'), None)
        if windows:
            text(c, 591, 249, f"Windows: {windows['passed']}/{windows['total']}", 13, CREAM, 'Consolas')
    else:
        text(c, 591, 315, 'No verified saved repair plan', 13, CREAM, 'Consolas')
        text(c, 591, 277, 'Repair: unresolved', 17, ORANGE, 'ConsolasBold')
        text(c, 591, 249, 'CI gate verified separately', 13, CREAM, 'Consolas')
    text(c, 591, 215, 'BOB CONTRIBUTION', 11, LIME, 'ConsolasBold')
    for index, line in enumerate(wrap_lines(evidence['bob_contribution'], 36, 3)):
        text(c, 591, 190 - index * 20, line, 12, CREAM)
    if report:
        text(c, 591, 112, f"Plan SHA: {report['plan_hash'][:15]}...", 10, MUTED, 'Consolas')
    else:
        text(c, 591, 112, 'No Parcel pass claimed.', 10, MUTED, 'Consolas')
    c.showPage()


def ci_slide(c, evidence):
    ci = evidence['ci_evidence']
    base(c, 9, 'A PR gate that keeps the counterexample.',
         '08  /  VERIFIED BOB-BUILT REVIEW WORKFLOW', final=True)
    box(c, 45, 171, 438, 203, PANEL, '#516452')
    with Image.open(ci['bob_ci_summary_image']) as screenshot:
        width, height = screenshot.size
    scale = min(410 / width, 173 / height)
    drawn_w, drawn_h = width * scale, height * scale
    c.drawImage(str(ci['bob_ci_summary_image']), 59 + (410 - drawn_w) / 2,
                185 + (173 - drawn_h) / 2, width=drawn_w, height=drawn_h)
    text(c, 59, 386, 'ACTUAL BOB IDE TASK SUMMARY', 10, LIME, 'ConsolasBold')
    text(c, 48, 144, f"Task {ci['bob_ci_task_id']}", 11, MUTED, 'Consolas')
    cards = [
        ('unsafe', 'UNSAFE / RED', ORANGE),
        ('safe_reference', 'SAFE REFERENCE / GREEN', LIME),
        ('regressed', 'REGRESSION / RED', ORANGE),
    ]
    for index, (control, label, color) in enumerate(cards):
        run = ci['runs'][control]
        y = 301 - index * 91
        box(c, 510, y, 405, 78)
        text(c, 525, y + 49, label, 11, color, 'ConsolasBold')
        text(c, 525, y + 21,
             f"{run['passed']}/{run['total']} probes  |  run #{run['run']}",
             12, CREAM, 'Consolas')
        c.linkURL(run['url'], (510, y, 915, y + 78), relative=0)
    text(c, 45, 93,
         'Every run retained JSON, Markdown, ZIP and an independently replayed report.',
         13, CREAM)
    text(c, 45, 66, 'Controls use pre-event synthetic plans; the PR gate was built in Bob.',
         12, MUTED)
    c.showPage()


def plan_label(plan):
    label = plan.get('name', 'unnamed')
    return label[:25] + ('...' if len(label) > 25 else '')


def wrap_lines(value, width, limit):
    lines = textwrap.wrap(value, width=width, break_long_words=True, break_on_hyphens=False)
    if len(lines) > limit:
        lines = lines[:limit]
        lines[-1] = lines[-1][:width - 3] + '...'
    return lines


def deck(evidence=None, output=None):
    register_fonts()
    final = evidence is not None
    dest = Path(output) if output else ROOT / 'work' / ('deck-final.pdf' if final else 'deck-draft.pdf')
    dest.parent.mkdir(exist_ok=True)
    c = canvas.Canvas(str(dest), pagesize=(W, H))
    c.drawImage(str(HERE / 'cover.png'), 0, 0, width=W, height=H)
    c.showPage()

    base(c, 2, 'The release is not one moment.', '01  /  PROBLEM', final)
    text(c, 45, 360, 'A new-version test can pass while an old worker is still writing.', 20)
    text(c, 45, 329, 'GitLab documented canary QA passing while older production instances failed inserts.',
         13, MUTED)
    text(c, 45, 307, 'Source: docs.gitlab.com/development/multi_version_compatibility/',
         10, LIME, 'Consolas')
    c.linkURL('https://docs.gitlab.com/development/multi_version_compatibility/#downtime-on-release-features-between-canary-and-production-deployment',
              (45, 303, 650, 321), relative=0)
    steps = [
        (45, '01', 'ADD COLUMN', 'The new field now exists.'),
        (338, '02', 'BACKFILL', 'Rows are copied once.'),
        (631, '03', 'INSTALL SYNC', 'The two fields now agree.'),
    ]
    for x, n, title, body in steps:
        box(c, x, 184, 273, 111)
        text(c, x + 18, 263, n, 13, LIME, 'ConsolasBold')
        text(c, x + 18, 228, title, 17, CREAM, 'ConsolasBold')
        text(c, x + 18, 202, body, 12, MUTED)
    box(c, 352, 82, 553, 74, '#563c33', ORANGE)
    text(c, 370, 128, 'THE GAP: old worker writes after backfill', 18, CREAM, 'SegoeBold')
    text(c, 370, 101, 'The new field is stale even though the migration succeeds.', 13, RED)
    c.showPage()

    base(c, 3, 'The plan looked green. The data disagreed.', '02  /  REPRODUCED COUNTEREXAMPLE', final)
    box(c, 45, 245, 412, 120)
    text(c, 67, 311, '76/76', 45, LIME, 'ConsolasBold')
    text(c, 67, 274, 'completed-rollout probes passed', 16, MUTED)
    box(c, 482, 245, 433, 120, '#563c33', ORANGE)
    text(c, 505, 311, '32/48', 45, ORANGE, 'ConsolasBold')
    text(c, 505, 274, 'migration-window probes passed', 16, CREAM)
    text(c, 45, 207, 'One failing replay, simplified', 16, CREAM, 'SegoeBold')
    for x, label in [(45, 'ADD COLUMN'), (265, 'BACKFILL'), (485, 'OLD WRITE'), (705, 'ADD SYNC')]:
        box(c, x, 148, 198, 42, '#563c33' if label == 'OLD WRITE' else PANEL)
        text(c, x + 12, 163, label, 12, ORANGE if label == 'OLD WRITE' else CREAM, 'ConsolasBold')
    text(c, 45, 106, 'Expected latest address: 18 Marina Road', 16, LIME, 'Consolas')
    text(c, 45, 77, 'Observed by new reader: 4 Broad Street', 16, RED, 'Consolas')
    c.showPage()

    base(c, 4, 'Make the handover executable.', '03  /  ENGINE', final)
    items = [
        (45, 'FIXED OLD CONTRACT', 'Old reads, updates and inserts'),
        (339, 'CANDIDATE PLAN', 'Migration + new SQL adapter'),
        (633, 'INDEPENDENT LEDGER', 'Every acknowledged write'),
    ]
    for x, title, body in items:
        box(c, x, 292, 278, 83)
        text(c, x + 16, 341, title, 13, LIME, 'ConsolasBold')
        text(c, x + 16, 310, body, 12, CREAM)
    text(c, 45, 244, 'Fresh SQLite database for each schedule and string input.', 20)
    text(c, 45, 208, 'Old writes are inserted at every migration statement boundary.', 20)
    c.setStrokeColor(HexColor(ORANGE))
    c.line(45, 175, 915, 175)
    text(c, 45, 145, 'OUTPUT', 12, ORANGE, 'ConsolasBold')
    text(c, 45, 111, 'Exact SQL + inputs + expected/observed values + replay prefix.', 18)
    text(c, 45, 78, 'Passing means only these contracts and schedules passed.', 14, MUTED)
    c.showPage()

    base(c, 5, 'What changed the verdict?', '04  /  MEASURED SAMPLE RESULTS', final)
    text(c, 51, 350, 'Candidate', 14, MUTED, 'ConsolasBold')
    text(c, 528, 350, 'Completed', 14, MUTED, 'ConsolasBold')
    text(c, 733, 350, 'Windows', 14, MUTED, 'ConsolasBold')
    rows = []
    sample_reports = []
    for label, candidate in (
        ('Direct rename', 'rename'),
        ('One-time backfill', 'backfill'),
        ('Late bridge', 'late_bridge'),
        ('Window-safe bridge (reference)', 'bridge'),
    ):
        plan = json.loads((ROOT / 'examples' / 'parcel' / f'{candidate}.json').read_text(encoding='utf-8'))
        report = run_rehearsal('parcel', plan)
        completed = [row for row in report['results'] if row['category'] != 'migration_window']
        windows = [row for row in report['results'] if row['category'] == 'migration_window']
        rows.append((label,
                     f"{sum(row['passed'] for row in completed)}/{len(completed)}",
                     f"{sum(row['passed'] for row in windows)}/{len(windows)}"))
        sample_reports.append(report)
    for i, (name, complete, windows) in enumerate(rows):
        y = 281 - i * 53
        box(c, 45, y, 870, 44, '#563c33' if i == 2 else PANEL)
        text(c, 60, y + 13, name, 15 if i == 3 else 17,
             CREAM, 'SegoeBold' if i in (2, 3) else 'Segoe')
        text(c, 540, y + 13, complete, 17, LIME, 'ConsolasBold')
        text(c, 748, y + 13, windows, 17, ORANGE if i == 2 else LIME, 'ConsolasBold')
    baseline_detected = sum(r['baseline']['passed'] < r['baseline']['total'] for r in sample_reports[:3])
    completed_detected = sum(any(not row['passed'] for row in r['results']
                                 if row['category'] != 'migration_window') for r in sample_reports[:3])
    full_detected = sum(r['status'] == 'blocked' for r in sample_reports[:3])
    text(c, 45, 81, f'Curated unsafe patterns caught: baseline {baseline_detected}/3  |  rollout {completed_detected}/3  |  windows {full_detected}/3', 13, ORANGE, 'Consolas')
    text(c, 45, 59, 'Pre-event reference; curated samples, not Bob output or a customer benchmark.', 11, MUTED)
    c.showPage()

    warehouse = ROOT / 'examples' / 'warehouse'
    contract = json.loads((warehouse / 'contract.json').read_text(encoding='utf-8'))
    late_plan = json.loads((warehouse / 'late_bridge.json').read_text(encoding='utf-8'))
    safe_plan = json.loads((warehouse / 'bridge.json').read_text(encoding='utf-8'))
    late = run_rehearsal('custom', late_plan, contract)
    safe = run_rehearsal('custom', safe_plan, contract)
    if (late['status'], late['passed'], late['total'], safe['status'], safe['passed'], safe['total']) != (
            'blocked', 108, 124, 'pass', 124, 124):
        raise ValueError('Warehouse slide evidence has changed; review its claims before building the deck')
    witness = late['witness']['failure']
    expected = witness['expected']['11']
    observed = witness['actual']['11']
    base(c, 6, 'Bring your own release contract.', '05  /  VALIDATED CLI IMPORT', final)
    box(c, 45, 206, 870, 174)
    text(c, 63, 348, 'WAREHOUSE / BIN RELOCATION', 13, LIME, 'ConsolasBold')
    text(c, 63, 313, 'Old scanner workers update pick_bin while new workers read fulfillment_bin.', 17)
    text(c, 63, 272, 'Late bridge', 17, CREAM, 'SegoeBold')
    text(c, 244, 272, f"{late['passed']}/{late['total']}  BLOCKED", 19, ORANGE, 'ConsolasBold')
    text(c, 63, 235, 'Window-safe ordering', 17, CREAM, 'SegoeBold')
    text(c, 298, 235, f"{safe['passed']}/{safe['total']}  PASS", 19, LIME, 'ConsolasBold')
    text(c, 45, 168, f'Old write acknowledged: {expected}   /   New read observed: {observed}', 18, ORANGE)
    text(c, 45, 119, 'JSON + Markdown carry the same executed report, SQL, inputs and hashes.', 16)
    text(c, 45, 78,
         'Pre-event Codex importer and reference plans; Bob repair is shown on the next slide.'
         if final else 'Pre-event Codex importer and reference plans; Bob repair remains an event task.',
         13, MUTED)
    c.showPage()

    if final:
        bob_slide(c, evidence)
    else:
        base(c, 7, 'Bob must earn the pass.', '06  /  LIVE HACKATHON WORKFLOW')
        box(c, 45, 335, 870, 45, '#563c33', ORANGE)
        text(c, 62, 350, 'PENDING: event-period Bob task. Replace with observed session evidence.', 14, CREAM, 'SegoeBold')
        for y, n, title, detail in [
            (268, '01', 'Diagnose', 'Bob calls Cutover MCP tools on the late-bridge failure.'),
            (194, '02', 'Repair', 'Bob proposes its own candidate; failed attempts are retained.'),
            (120, '03', 'Verify', 'Run the fixed suite, import its plan, and show actual task summary.'),
        ]:
            text(c, 53, y, n, 26, ORANGE, 'ConsolasBold')
            text(c, 111, y + 3, title, 20, CREAM, 'SegoeBold')
            text(c, 270, y + 5, detail, 14, MUTED)
        c.showPage()

    base(c, 8, 'A review step for schema-changing PRs.', '07  /  USER AND ADOPTION', final)
    box(c, 45, 247, 412, 117)
    text(c, 64, 328, 'USER', 13, LIME, 'ConsolasBold')
    text(c, 64, 298, 'Backend / release engineer', 21, CREAM, 'SegoeBold')
    text(c, 64, 269, 'Shipping a schema change with old workers alive.', 12, MUTED)
    box(c, 482, 247, 433, 117)
    text(c, 501, 328, 'VERIFIED WORKFLOW' if final and evidence.get('ci_evidence')
         else 'PROPOSED WORKFLOW', 13, LIME, 'ConsolasBold')
    text(c, 501, 298, 'PR review + CI rehearsal', 21, CREAM, 'SegoeBold')
    text(c, 501, 269, 'Attach a witness and bounded evidence.', 12, MUTED)
    text(c, 45, 210, 'Revenue hypothesis: paid per-repository CI checks; demand unvalidated.', 17)
    text(c, 45, 180, 'Next: release-team interviews and a real repository adapter.', 16)
    text(c, 45, 139, 'Limits: SQLite single-table contracts; no concurrency, locks,', 14, MUTED)
    text(c, 45, 116, 'mid-statement failure, performance or production safety claim.', 14, MUTED)
    text(c, 45, 68, 'github.com/josepha-mayo/cutover', 15, LIME, 'Consolas')
    c.showPage()
    if final and evidence.get('ci_evidence'):
        ci_slide(c, evidence)
    c.save()
    return dest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', help='Path to observed Bob artifact manifest for final deck')
    parser.add_argument('--output', help='PDF output path')
    args = parser.parse_args()
    observed = event_evidence(args.evidence) if args.evidence else None
    cover()
    print(HERE / 'cover.png')
    print(deck(observed, args.output))
