# Current status — September 23, 2026

## Working and verified

- Local browser application with editable migration and application queries.
- Real disposable SQLite executions and independent write-ledger comparisons.
- 19 completed-rollout schedules × 4 inputs = 76 probes, plus old updates and inserts at every migration statement boundary.
- Two sample contracts and four clearly labelled reference candidates.
- Real SQL errors, semantic mismatches, rollback-read evidence and selectable replay details.
- Candidate import/save, JSON evidence export, and a Bob task-preparation dialog.
- Project-local Bob custom mode and MCP configuration generator.
- Official MCP SDK v1.30.0 connection: initialization, discovery, all three tools, actual candidate execution and invalid-input errors checked with an SDK client.
- 20 Python tests passed on Python 3.14.7 / Windows, including migration-window detection and HTTP behavior.
- Browser verification in Brave using computer use: backfill failure; bridge pass; manually edited bridge blocked with 12 failures; stale results invalidated when editing; evidence filter; Bob dialog; JSON file import and rerun; exported JSON downloaded and inspected.
- Actual desktop screenshots inspected. At a 390-pixel mobile viewport, imported-candidate execution passed, the layout stacked correctly, and DOM measurements found no horizontal overflow. Temporary viewport override restored afterward.

## Measured outcomes for both sample contracts

| Candidate | Same-version baseline | Completed rollout | Migration windows | Total |
| --- | --- | --- | --- | --- |
| Direct rename | 8/8 | 16/76 | 8/16 | 24/92 |
| Expand + one-time backfill | 8/8 | 48/76 | 16/24 | 64/100 |
| Late bridge | 8/8 | 76/76 | 32/48 | 108/124 |
| Window-safe bridge | 8/8 | 76/76 | 48/48 | 124/124 |

The late bridge is the key counterexample: all completed-rollout checks pass, but an old write between backfill and trigger creation leaves stale data. The baseline is a deliberately narrower set of synthetic checks, not an existing customer's CI history. Totals vary with migration statement count. These outcomes measure detection within the fixed samples, not general incident reduction or developer time savings.

## Remaining before submission

1. Obtain Bob access and capture a real Bob contribution. Approval is confirmed; access invitation was not found in email searches. Event materials advertise access at kickoff.
2. Independently assess Bob's saved candidate with the fixed engine. Keep failed candidates and task-summary screenshots.
3. Confirm kickoff-specific build-period rules. Disclose this pre-event Codex preparation. A solo Cutover team has been created on the event page.
4. Publish the repository and deploy the Render free service; verify from a fresh browser without local state. Vercel was signed into but is paused for Hobby fair-use limits.
5. Produce the final recorded video, PDF slides and cover image using actual Bob evidence.
6. Submit by September 27, 2026 at 16:00 West Africa Time according to the currently displayed event schedule. September 24 is registration close, not submission close.
7. After qualified submission, complete the event feedback form to enter the separately advertised 20 × $100 random draw. The September 23 email says both actions are required; wait for the form and give real feedback.

## Important limits

- The prototype uses SQLite SQL contracts, not full application processes or a real rolling deployment.
- No concurrent transactions, lock contention, mid-statement interruption, final contract-phase execution, or PostgreSQL/MySQL coverage.
- The HTTP server is a local demo server. It has request-size/origin checks and bounded candidate execution, but public multi-tenant resource isolation and deployment have not been verified.
- A passing reference plan is not proof of Bob authorship. No actual Bob host session has been run.
- Browser download-event instrumentation timed out, but the browser-created JSON file was found on disk and its content was verified. Browser screenshot capture in Codex's in-app browser was unavailable, so visual verification used Brave successfully.
- Linux/macOS and hosted deployment have not been run. No submission has been made. The project submission page currently says it is available only during the active phase.

## Local continuation

Project: `outputs/cutover` in this task's workspace.

Start: `python server.py --port 8765` from the project folder.

App: `http://127.0.0.1:8765`.

Optional MCP environment prepared in this task's `work/cutover-venv`. The generated `.bob/mcp.json` points to that environment; it is machine-specific and excluded from version control. Recreate with `configure_bob.py` after relocating the project.

See `BOB_TASK.md` for the exact next session and `SUBMISSION.md` for draft narrative and recording sequence. The next most valuable work is a real Bob repair and a live, independently verified hosted demo.
