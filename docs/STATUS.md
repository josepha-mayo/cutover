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
- 30 Python tests passed on Python 3.14.7 / Windows, including migration-window detection, HTTP behavior, excluding comment-only SQL from coverage, and adversarial new-adapter contract checks.
- Browser verification in Brave using computer use: backfill failure; bridge pass; manually edited bridge blocked with 12 failures; stale results invalidated when editing; evidence filter; Bob dialog; JSON file import and rerun; exported JSON downloaded and inspected.
- Actual desktop screenshots inspected. At a 390-pixel mobile viewport, imported-candidate execution passed, the layout stacked correctly, and DOM measurements found no horizontal overflow. Temporary viewport override restored afterward.
- Public [GitHub repository](https://github.com/josepha-mayo/cutover) and passing [Windows/Ubuntu CI](https://github.com/josepha-mayo/cutover/actions) on Python 3.12 for the v0.2.4 code.
- [Render free demo](https://cutover-rehearsal.onrender.com/) deployed and checked in a fresh browser: late bridge 108/124 blocked, window-safe bridge 124/124 passed.
- 16:9 cover image generated and visually inspected. An eight-page PDF deck draft exists locally; its Bob slide is prominently marked pending and must be replaced with real session evidence before submission. A separate slide shows the imported warehouse contract and labels it as pre-event Codex work.
- Narrow-screen browser retest at a 304-pixel viewport: the safe candidate rendered and ran 124/124 without horizontal overflow after mobile grid and coverage fixes.
- After the v0.2.2 deployment, the in-app browser showed the backfill blocked at 48/100 and the safe bridge passing 124/124; its replay visibly includes the fixed `target.check` postcondition. A direct request to the public API also blocked the no-op old-adapter plan at 0/92 with `adapter_contract` evidence.
- September 23 public-browser retest: Parcel and Relay late bridges each blocked at 108/124, with 76/76 completed-rollout probes passing and 16 migration-window probes failing. Parcel's shortest replay showed the acknowledged old write and the stale new read. Parcel's window-safe bridge passed 124/124 on the deployed service. A 304-pixel in-app browser screenshot showed the stacked mobile verdict without visible horizontal overflow.
- The default browser scenario now opens on the late bridge so a first-click rehearsal exposes the missed migration-window write. A local browser run showed 108/124 overall, including 76/76 completed-rollout probes and 32/48 window probes, with the shortest replay showing `18 Marina Road` expected and `4 Broad Street` observed. Responsive checks at 390, 946 and 1366 CSS pixels found no horizontal overflow; the temporary browser viewport override was restored.
- Engine v0.2.3 closes a further false pass found in review: a new reader returning old-column data while touching the target only in a no-op expression had passed 124/124. The fixed evaluator rejects old-column reads by the new reader; both sample contracts and the subprocess worker now block that adversarial candidate. Compact evidence and the controlled ablation were regenerated against the new engine hash, which is stable across Windows and Linux line endings.
- Engine v0.2.4 closes two analogous false passes: a new updater self-assigning the target while writing the old column, and a new insert writing only the old column, each previously passed 124/124 by relying on synchronization triggers. A trigger-free shadow now checks that every new update and insert carries its value to the target. Both patterns are blocked in both sample contracts; an explicit dual-write and the passing reference still pass 124/124. The checked-in evidence was regenerated against the v0.2.4 engine hash.
- The deployed Render API was checked after the v0.2.3 release: the safe Parcel plan passed 124/124, the adversarial old-column reader was blocked with 0/8 baseline checks passing, and both responses reported engine hash `58c8851507a8ea45b4aa1a0aa80fb400036d6b465271ffe27436d8d2c26b7cdf`.
- The deployed Render API now reports v0.2.4 and engine hash `16a6e171b8fa7a35f76d71f4ffc4940bf8787c8254cc1a4116376ca6b8e540ed`. The safe Parcel reference passed 124/124; the masked new updater blocked at 92/124 and the old-only new insert blocked at 116/124, with 4/8 same-version baseline checks passing for each adversarial plan.
- Reproducible [controlled detection ablation](IMPACT.md) on three deliberately unsafe patterns: new-version baseline detects 0/3, completed-rollout checks 2/3, full suite 3/3 in each structurally similar sample.
- A v0.2.4 reference-withheld Bob repair workspace can be generated from clean committed Git blobs. The verifier has matched all 18 copied files to source, confirmed the passing reference plans are absent, and recorded evaluator SHA-256 `16a6e171b8fa7a35f76d71f4ffc4940bf8787c8254cc1a4116376ca6b8e540ed`. An SDK client launched the generated workspace's exact `.bob/mcp.json` command, discovered all three tools, and received the expected `window_write_after_2-0` witness. The workspace generator was also exercised from a separate CRLF checkout and verified. Re-freeze from the latest clean commit at kickoff. This is pre-event setup, not a Bob IDE session.
- IBM Bob IDE 2.1.0 was installed on the Windows host on September 23 from the official IBM download. The installed executable reports version `1.126.0+bob2.1.0` and has a valid IBM code signature. After the user signed up for a free trial, the IDE showed its authenticated task composer rather than the login prompt. An IBM email on September 23 confirms the trial is ready and lists October 23, 2026 as its expiration. Hackathon-specific access, trial capacity at kickoff, and a Bob task remain unverified. No paid subscription is authorized.
- Bob Shell 2.0.4 was installed locally in this task's private `../../work/bob-shell/` directory, outside the public repo, from IBM's official package after matching IBM's published SHA-256 checksum. Its `--version` works and `mcp list` discovers the prepared workspace's Cutover server. IBM documents shared task history between Shell and IDE, providing a possible route to machine-readable tool evidence and IDE screenshots. Shell license acceptance, authentication, actual Bob MCP execution, and task-history sharing remain unverified; no Bob task was run.
- The earlier [May 2026 IBM Bob hackathon guide](https://watsonx-hackathons-2026.s3.us.cloud-object-storage.appdomain.cloud/Lablab-IBM-Bob-hackathon-guide-May-2026.pdf) explicitly required Bob IDE use plus a task-consumption screenshot and exported Markdown history for each relevant task in a `bob_sessions/` repository folder. This is a preparation precedent, not a September 2026 rule. The folder and capture instructions are prepared; the new event brief must be checked at kickoff.
- A three-minute [demo shot list](../presentation/recording-plan.md) and [local neural narration workflow](../presentation/VOICE.md) are prepared. Isolated browser-only takes of the public Render app checked Direct rename at `24 / 92` and Late bridge at `108 / 124`. A 22-second cropped proof clip shows the acknowledged old write followed by the expected `18 Marina Road` versus observed `4 Broad Street` read. Those takes and three slower-paced neural narration lines were assembled into an ignored 64-second prologue draft; its H.264/AAC format and representative cut-point frames were checked. A human listen is still needed. These pre-event drafts cannot serve as Bob evidence. Bob IDE window-only footage awaits the real session, and the final narration still requires real Bob results.
- All five non-Bob narration segments now fit the 180-second timeline at voice speed 0.82; the closing line ends at 179.26 seconds. The Bob lines remain pending, and subjective voice quality still needs a human listen. The current eight-page PDF draft still marks the Bob slide PENDING. The final deck checks the evaluator hash using the same line-ending normalization as the engine and reruns the claimed candidate in a fresh bounded worker before accepting its detailed report.
- The sample-results slide labels the passing window-safe plan as a pre-event reference, and the [submission copy](SUBMISSION.md) separates provisional form fields from the still-unobserved Bob outcome.
- The [MP4 assembler](../presentation/assemble_video.py) produced a verified 1920×1080, 30 fps H.264/AAC four-second test with synthetic red/blue clips and audio. The test confirmed cut order and duration only. The template rejects pending footage; no real Bob clip or final MP4 exists.
- The assembler now also checks that the finished MP4 has one H.264 1920×1080/30 fps video stream, one AAC audio stream, and is under the general 300 MB submission limit. A new four-second end-to-end synthetic render passed those checks. An existing signed-in YouTube Studio channel showed **Upload videos** on September 23, providing a likely unlisted-video link route; no final upload or signed-out playback has been tested.
- The 64-second public-demo prologue has been aligned with the submission script: Direct rename occupies 0:00–0:18, Late bridge 0:18–0:42, and the real stale-read replay 0:42–1:04. The remaining Bob-specific footage is still pending. Commit `c187db8` passed both Windows and Ubuntu CI; the public Render page was independently rerun afterward and showed Direct rename at 24/92 with 68 failures and Late bridge at 108/124 with 16 migration-window failures.
- IBM Bob IDE opened the reference-withheld `cutover-bob-session-180246e0` workspace. The user trusted this folder on September 23; the Restricted Mode banner disappeared. Bob Settings showed the free trial with full remaining capacity, MCP enabled for new tasks, and the project-scoped `cutover` server **Connected**. The source-side 18-file integrity audit still passes. A read-only pre-event diagnostic prompt was drafted in Bob but has **not** been sent; no MCP call from Bob, candidate, task summary, or event-period evidence has been captured. Re-freeze from the latest clean commit when the event starts.
- A fresh pre-event workspace was frozen from clean commit `7a6a1e1` and passed the 18-file integrity/withheld-reference audit. A new SDK preflight launched that workspace's exact `.bob/mcp.json` command, found all three tools, received the `window_write_after_2-0` late-bridge witness, and confirmed the passing reference was rejected by the diagnostic tool. This is a local SDK client test, not an IBM Bob task.
- Pre-event Codex work now adds a validated CLI import path for a user-supplied single-table SQLite contract with domain-specific payloads and an old-adapter smoke check, plus Markdown review output from the same executed report object. The warehouse fixture's late synchronization blocks at 108/124 with `R-07` expected and `A-01` observed; its safe ordering passes 124/124. This is a third structurally similar fixture, not an independent production incident or Bob contribution. The public browser still supports only Parcel and Relay. The fresh event-period Bob extension is a browser import/replay workflow and, if time permits, a PR check example.
- Local v0.3 checks passed: 42 tests, a real MCP SDK preflight, the blocked and passing warehouse CLI runs, evidence regeneration, and visual inspection of the new deck slide. CI now exercises the imported passing contract on both operating systems and uploads its JSON and Markdown reports; the remote CI result is pending the push.

## Measured outcomes for both sample contracts

| Candidate | Same-version baseline | Completed rollout | Migration windows | Total |
| --- | --- | --- | --- | --- |
| Direct rename | 8/8 | 16/76 | 8/16 | 24/92 |
| Expand + one-time backfill | 8/8 | 32/76 | 16/24 | 48/100 |
| Late bridge | 8/8 | 76/76 | 32/48 | 108/124 |
| Window-safe bridge | 8/8 | 76/76 | 48/48 | 124/124 |

The late bridge is the key counterexample: all completed-rollout checks pass, but an old write between backfill and trigger creation leaves stale data. The baseline is a deliberately narrower set of synthetic checks, not an existing customer's CI history. Totals vary with migration statement count. These outcomes measure detection within the fixed samples, not general incident reduction or developer time savings.

## Remaining before submission

1. Check Bob's trial capacity, hackathon access, and the September evidence rules at kickoff, then capture a real event-period Bob contribution. Event approval is confirmed; a separate access invitation was not found in email searches. Do not purchase a paid subscription. Re-freeze from the latest clean commit because the older Bob workspaces do not include the new CLI/reporting modules.
2. Independently assess Bob's saved candidate with the fixed engine. Keep failed candidates and task-summary screenshots.
3. Confirm kickoff-specific build-period rules and update [PROVENANCE.md](PROVENANCE.md) with actual event-period Bob evidence. The September 23 Codex baseline is recorded there. A solo Cutover team has been created on the event page.
4. Record the real video and replace the placeholder Bob slide in the PDF deck draft with actual session evidence. Recheck the 16:9 cover against the submission form's image requirements.
5. Submit by September 27, 2026 at 16:00 West Africa Time according to the official live event page checked September 23. Registration closes at kickoff, September 25 at 16:00 West Africa Time.
6. After the event, complete its feedback form to enter the 20 × $100 participant reward draw, provided the project was qualified and submitted by the deadline. The current event page says the form comes after the event; wait for it and give real feedback.

## Important limits

- The prototype uses SQLite SQL contracts, not full application processes or a real rolling deployment.
- No concurrent transactions, lock contention, mid-statement interruption, final contract-phase execution, or PostgreSQL/MySQL coverage.
- The public HTTP service has request-size/origin checks and bounded candidate execution, but it is a sample-only hackathon demo without verified multi-tenant resource isolation. Render's free service can spin down after inactivity and take around a minute to wake.
- A passing reference plan is not proof of Bob authorship. No actual Bob host session has been run.
- Browser download-event instrumentation timed out, but the browser-created JSON file was found on disk and its content was verified. Visual checks used Brave earlier and the in-app browser during the September 23 public retest.
- CI ran on Ubuntu; macOS was not tested. No submission has been made. The project submission page currently says it is available only during the active phase.

## Local continuation

Project: `outputs/cutover` in this task's workspace.

Start: `python server.py --port 8765` from the project folder.

App: `http://127.0.0.1:8765`.

Optional MCP environment prepared in this task's `work/cutover-venv`. The generated `.bob/mcp.json` points to that environment; it is machine-specific and excluded from version control. Recreate with `configure_bob.py` after relocating the project.

See `BOB_TASK.md` for the exact next session and `SUBMISSION.md` for draft narrative and recording sequence. The next most valuable work is a real Bob repair and an evidence-backed presentation.
