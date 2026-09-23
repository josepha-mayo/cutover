"""Create the hackathon cover and a pre-event presentation draft.

The PDF deliberately marks the IBM Bob session as pending. Regenerate it with
actual session evidence before submission; do not present it as a final deck.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
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
    draw.text((1660, 968), 'v0.2 / SQLITE', font=font('consola.ttf', 17), fill=MUTED)
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


def base(c, number, title, kicker):
    c.setFillColor(HexColor(INK))
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(HexColor(ORANGE))
    c.rect(45, 505, 9, 9, fill=1, stroke=0)
    text(c, 63, 502, 'cutover.', 19, CREAM, 'SegoeBold')
    text(c, 666, 506, 'IBM BOB 2.0  /  DRAFT', 10, MUTED, 'Consolas')
    c.setStrokeColor(HexColor('#415246'))
    c.line(45, 485, 915, 485)
    text(c, 45, 451, kicker, 11, LIME, 'ConsolasBold')
    text(c, 45, 402, title, 34, CREAM, 'SegoeBold')
    c.line(45, 38, 915, 38)
    text(c, 45, 21, 'Pre-event draft. Bob session evidence still required.', 9, MUTED, 'Consolas')
    text(c, 883, 21, f'{number:02d}', 10, MUTED, 'Consolas')


def deck():
    register_fonts()
    dest = ROOT / 'work' / 'deck-draft.pdf'
    dest.parent.mkdir(exist_ok=True)
    c = canvas.Canvas(str(dest), pagesize=(W, H))
    c.drawImage(str(HERE / 'cover.png'), 0, 0, width=W, height=H)
    c.showPage()

    base(c, 2, 'The release is not one moment.', '01  /  PROBLEM')
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

    base(c, 3, 'The plan looked green. The data disagreed.', '02  /  REPRODUCED COUNTEREXAMPLE')
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

    base(c, 4, 'Make the handover executable.', '03  /  ENGINE')
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

    base(c, 5, 'What changed the verdict?', '04  /  MEASURED SAMPLE RESULTS')
    text(c, 51, 350, 'Candidate', 14, MUTED, 'ConsolasBold')
    text(c, 528, 350, 'Completed', 14, MUTED, 'ConsolasBold')
    text(c, 733, 350, 'Windows', 14, MUTED, 'ConsolasBold')
    rows = [
        ('Direct rename', '16/76', '8/16'),
        ('One-time backfill', '48/76', '16/24'),
        ('Late bridge', '76/76', '32/48'),
        ('Window-safe bridge', '76/76', '48/48'),
    ]
    for i, (name, complete, windows) in enumerate(rows):
        y = 281 - i * 53
        box(c, 45, y, 870, 44, '#563c33' if i == 2 else PANEL)
        text(c, 60, y + 13, name, 17, CREAM, 'SegoeBold' if i in (2, 3) else 'Segoe')
        text(c, 540, y + 13, complete, 17, LIME, 'ConsolasBold')
        text(c, 748, y + 13, windows, 17, ORANGE if i == 2 else LIME, 'ConsolasBold')
    text(c, 45, 81, 'Curated unsafe patterns caught: baseline 0/3  |  rollout 2/3  |  windows 3/3', 13, ORANGE, 'Consolas')
    text(c, 45, 59, 'Two structurally similar samples; no customer benchmark.', 11, MUTED)
    c.showPage()

    base(c, 6, 'Bob must earn the pass.', '05  /  LIVE HACKATHON WORKFLOW')
    box(c, 45, 335, 870, 45, '#563c33', ORANGE)
    text(c, 62, 350, 'PENDING: access begins at kickoff. Replace this slide with real session evidence.', 14, CREAM, 'SegoeBold')
    for y, n, title, detail in [
        (268, '01', 'Diagnose', 'Bob calls Cutover MCP tools on the late-bridge failure.'),
        (194, '02', 'Repair', 'Bob proposes its own candidate; failed attempts are retained.'),
        (120, '03', 'Verify', 'Run the fixed suite, import its plan, and show actual task summary.'),
    ]:
        text(c, 53, y, n, 26, ORANGE, 'ConsolasBold')
        text(c, 111, y + 3, title, 20, CREAM, 'SegoeBold')
        text(c, 270, y + 5, detail, 14, MUTED)
    c.showPage()

    base(c, 7, 'A review step for schema-changing PRs.', '06  /  USER AND ADOPTION')
    box(c, 45, 247, 412, 117)
    text(c, 64, 328, 'USER', 13, LIME, 'ConsolasBold')
    text(c, 64, 298, 'Backend / release engineer', 21, CREAM, 'SegoeBold')
    text(c, 64, 269, 'Shipping a schema change with old workers alive.', 12, MUTED)
    box(c, 482, 247, 433, 117)
    text(c, 501, 328, 'PROPOSED WORKFLOW', 13, LIME, 'ConsolasBold')
    text(c, 501, 298, 'PR review + CI rehearsal', 21, CREAM, 'SegoeBold')
    text(c, 501, 269, 'Attach a witness and bounded evidence.', 12, MUTED)
    text(c, 45, 204, 'Next validation: real repository adapter and engineer feedback.', 18)
    text(c, 45, 165, 'Limits: SQLite samples; no concurrency, locks, mid-statement failure,', 14, MUTED)
    text(c, 45, 142, 'performance, final column removal or production safety claim.', 14, MUTED)
    text(c, 45, 82, 'github.com/josepha-mayo/cutover', 15, LIME, 'Consolas')
    c.showPage()
    c.save()
    return dest


if __name__ == '__main__':
    cover()
    print(HERE / 'cover.png')
    print(deck())
