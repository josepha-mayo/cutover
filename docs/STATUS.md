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
- 25 Python tests passed on Python 3.14.7 / Windows, including migration-window detection, HTTP behavior, excluding comment-only SQL from coverage, and rejecting old-column-only plans that previously produced a false pass.
- Browser verification in Brave using computer use: backfill failure; bridge pass; manually edited bridge blocked with 12 failures; stale results invalidated when editing; evidence filter; Bob dialog; JSON file import and rerun; exported JSON downloaded and inspected.
- Actual desktop screenshots inspected. At a 390-pixel mobile viewport, imported-candidate execution passed, the layout stacked correctly, and DOM measurements found no horizontal overflow. Temporary viewport override restored afterward.
- Public [GitHub repository](https://github.com/josepha-mayo/cutover) and passing [Windows/Ubuntu CI](https://github.com/josepha-mayo/cutover/actions/runs/35862278659) on Python 3.12.
- [Render free demo](https://cutover-rehearsal.onrender.com/) deployed and checked in a fresh browser: late bridge 108/124 blocked, window-safe bridge 124/124 passed.
- 16:9 cover image generated and visually inspected. A seven-page PDF deck draft exists locally; its Bob slide is prominently marked pending and must be replaced with real session evidence before submission.
- Narrow-screen browser retest at a 304-pixel viewport: the safe candidate rendered and ran 124/124 without horizontal overflow after mobile grid and coverage fixes.
- After the v0.2.2 deployment, the in-app browser showed the backfill blocked at 48/100 and the safe bridge passing 124/124; its replay visibly includes the fixed `target.check` postcondition. A direct request to the public API also blocked the no-op old-adapter plan at 0/92 with `adapter_contract` evidence.
- Reproducible [controlled detection ablation](IMPACT.md) on three deliberately unsafe patterns: new-version baseline detects 0/3, completed-rollout checks 2/3, full suite 3/3 in each structurally similar sample.
- Current reference-withheld Bob repair workspace prepared as sibling `cutover-bob-session-c1395b51` from commit `c1395b5`. The generated manifest records evaluator SHA-256 `fc2e487d555e723b5500e06346eaad3ceee220954ee9ebd7ba7674aaf887f774`; no passing reference plan was copied, and the late bridge still blocks at 108/124. Earlier session workspaces remain on disk but use older evaluators and should not be used for the event session. This is pre-event setup, not a Bob session.
- IBM Bob IDE 2.1.0 was installed on the Windows host on September 23 from the official IBM download. The installed executable reports version `1.126.0+bob2.1.0`, has a valid IBM code signature, and was running after setup exited. Authentication, hackathon access, and a Bob task remain unverified.

## Measured outcomes for both sample contracts

| Candidate | Same-version baseline | Completed rollout | Migration windows | Total |
| --- | --- | --- | --- | --- |
| Direct rename | 8/8 | 16/76 | 8/16 | 24/92 |
| Expand + one-time backfill | 8/8 | 32/76 | 16/24 | 48/100 |
| Late bridge | 8/8 | 76/76 | 32/48 | 108/124 |
| Window-safe bridge | 8/8 | 76/76 | 48/48 | 124/124 |

The late bridge is the key counterexample: all completed-rollout checks pass, but an old write between backfill and trigger creation leaves stale data. The baseline is a deliberately narrower set of synthetic checks, not an existing customer's CI history. Totals vary with migration statement count. These outcomes measure detection within the fixed samples, not general incident reduction or developer time savings.

## Remaining before submission

1. Obtain Bob access and capture a real Bob contribution. Approval is confirmed; access invitation was not found in email searches. Event materials advertise access at kickoff.
2. Independently assess Bob's saved candidate with the fixed engine. Keep failed candidates and task-summary screenshots.
3. Confirm kickoff-specific build-period rules and update [PROVENANCE.md](PROVENANCE.md) with actual event-period Bob evidence. The September 23 Codex baseline is recorded there. A solo Cutover team has been created on the event page.
4. Record the real video and replace the placeholder Bob slide in the PDF deck draft with actual session evidence. Recheck the 16:9 cover against the submission form's image requirements.
5. Submit by September 27, 2026 at 16:00 West Africa Time according to the currently displayed event schedule. September 24 is registration close, not submission close.
6. After the event, complete its feedback form to enter the 20 × $100 participant reward draw, provided the project was qualified and submitted by the deadline. The current event page says the form comes after the event; wait for it and give real feedback.

## Important limits

- The prototype uses SQLite SQL contracts, not full application processes or a real rolling deployment.
- No concurrent transactions, lock contention, mid-statement interruption, final contract-phase execution, or PostgreSQL/MySQL coverage.
- The public HTTP service has request-size/origin checks and bounded candidate execution, but it is a sample-only hackathon demo without verified multi-tenant resource isolation. Render's free service can spin down after inactivity and take around a minute to wake.
- A passing reference plan is not proof of Bob authorship. No actual Bob host session has been run.
- Browser download-event instrumentation timed out, but the browser-created JSON file was found on disk and its content was verified. Browser screenshot capture in Codex's in-app browser was unavailable, so visual verification used Brave successfully.
- CI ran on Ubuntu; macOS was not tested. No submission has been made. The project submission page currently says it is available only during the active phase.

## Local continuation

Project: `outputs/cutover` in this task's workspace.

Start: `python server.py --port 8765` from the project folder.

App: `http://127.0.0.1:8765`.

Optional MCP environment prepared in this task's `work/cutover-venv`. The generated `.bob/mcp.json` points to that environment; it is machine-specific and excluded from version control. Recreate with `configure_bob.py` after relocating the project.

See `BOB_TASK.md` for the exact next session and `SUBMISSION.md` for draft narrative and recording sequence. The next most valuable work is a real Bob repair and an evidence-backed presentation.
