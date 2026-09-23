# Submission preparation — not submitted

Working title: **Cutover: Rehearse the Release**

Short description (draft): Cutover finds the data failures a green build can miss. It replays old and new application versions through a database migration, gives IBM Bob an executable counterexample, and verifies the proposed repair.

## Pitch

Most application tests ask whether the new version works. During a rolling release, an older worker may still write to the same database. A migration can succeed and the new-version suite can pass while one worker sees stale data or a rollback loses visibility of a new write.

Cutover makes that handover executable. A fixed old-version contract and a proposed new adapter run against disposable SQLite databases. An independent ledger checks each acknowledged write. When a schedule fails, the engineer gets the SQL, inputs, expected data and observed data. A local MCP interface lets IBM Bob investigate the counterexample and submit a revised candidate to the same evaluator.

The current prototype covers two sample contracts, 19 completed-rollout schedules with four string inputs each, and old writes at every migration statement boundary. It detects direct schema breaks, stale data after a one-time backfill, and a late-bridge race that completed-rollout checks miss. Its result is bounded, reproducible evidence that supports review, not a claim of production safety. The intended user is a backend engineer shipping schema changes with long-lived workers.

**Update the Bob paragraph to describe only the session that was actually performed before publishing. No real Bob repair has been captured yet.**

## Demo script, target 3 minutes

- 0:00–0:20: “The new version passes. The old worker is still alive.” Show 8/8 baseline and 60 failing probes.
- 0:20–0:55: Apply the late bridge. Show all completed-rollout probes green, then open a failed migration-window replay: an old worker writes after backfill, before trigger creation.
- 0:55–1:45: Show real Bob diagnosis and candidate repair through MCP. Record only real actions, clearly distinguishing any edited video cuts.
- 1:45–2:20: Import Bob's actual plan. Execute all probes. Open the repaired migration-window replay. Remove one sync direction and rerun to show the evaluator is independent.
- 2:20–2:45: Export the report. Explain the target user and pull-request integration path.
- 2:45–3:00: Name the limits: statement boundaries, not concurrent transactions or mid-statement interruption. Show a concrete adoption path for review reports and future PostgreSQL adapters.

## Deck outline

1. A green build can still be a broken handover.
2. One-time backfills can miss writes from still-running workers.
3. Fixed contracts → executed schedules → counterexample → Bob repair → replay.
4. Controlled sample ablation: 0/3 unsafe patterns detected by the new-version baseline, 2/3 by completed-rollout checks, and 3/3 after migration windows. The late bridge passes 76/76 completed-rollout probes but fails 16/48 windows; the window-safe reference passes 124/124. Not a customer benchmark or Bob result.
5. Backend/release engineers; CI report and PR review are the initial adoption path. Demand and pricing remain unvalidated.
6. Real Bob contribution and precise prototype limits.

## Final artifacts

- Public repository with MIT license and setup instructions: [github.com/josepha-mayo/cutover](https://github.com/josepha-mayo/cutover).
- Public working demo: [cutover-rehearsal.onrender.com](https://cutover-rehearsal.onrender.com/). Render free may take around a minute to wake after inactivity; verify it again before submission and recording.
- [16:9 PNG cover](../presentation/cover.png) generated. Recheck image requirements on the actual form.
- Recorded MP4 demo and final PDF slide deck. A local seven-page PDF draft exists, with its Bob slide clearly marked pending. Replace that slide with real session evidence before submission. General submission guidance also mentions video links; verify the actual event form at submission.
- Actual Bob task-summary screenshots and Bob-assisted files.
- Cutover solo team created on lablab.ai; submission form remains unavailable until the active phase.
- After qualified submission, complete the IBM/lablab feedback form to enter the separately advertised 20 × $100 random draw.
- Final descriptions/tags and submission confirmation.

## Official constraints checked on September 23

The event runs September 25–27, 2026. The rendered schedule gives kickoff September 25 at 16:00 West Africa Time and submission close September 27 at 16:00. September 24 is the registration deadline. Current browser and approval email confirm enrollment/approval. Access details are advertised for kickoff; email searches found approval/registration messages but no access invitation.

The event requires a developer-workflow prototype and evidence of IBM Bob's role. It judges technology application, presentation, business value and originality. General lablab rules specify a public repository, online demo and presentation assets. The event page encourages preparation; confirm any additional build-period restrictions at kickoff and disclose pre-event work. The September 23 lablab email says the extra cash drawing requires a qualified submission and completed feedback form; it also reiterates that Bob access arrives at kickoff.

Sources: [event](https://lablab.ai/ai-hackathons/ibm-bob-2-hackathon), [rules](https://lablab.ai/hackathon-rules), [submission guide](https://lablab.ai/ai-articles/hackathon-guidelines), [Bob MCP configuration](https://bob.ibm.com/docs/ide/configuration/mcp/mcp-in-bob).
