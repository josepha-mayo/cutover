# Cutover submission copy — ready for final media and form review

Submitted title: **Cutover: Catch Lost Writes Before Merge**

Short description: **Cutover rehearses schema-changing releases with old and new workers, then uses IBM Bob to repair the missed-write window and build a PR gate that keeps the counterexample.**

Form links: public [demo](https://cutover-rehearsal.onrender.com/), [three-minute video](https://cutover-rehearsal.onrender.com/watch), [source](https://github.com/josepha-mayo/cutover), [deck](../presentation/cutover-submission.pdf), and [Bob IDE summaries](../bob_sessions/). Use the actual form's closest categories: developer tools, coding excellence, and pre-existing project, if those are offered. Technologies: IBM Bob IDE, MCP, Python, SQLite, JavaScript, GitHub Actions, Render.

The live September form must be checked before sending: it has separate project and Bob-usage narratives, media, source and demo fields. Keep each narrative within its visible character limits and verify links while signed out.

| Field | Prepared copy or gate |
| --- | --- |
| Title | **Cutover: Catch Lost Writes Before Merge** |
| Summary | The short description above. |
| Long description | The concise final project narrative below. |
| IBM Bob usage | The separate factual narrative below, with both task-summary PNGs and IDE histories in `bob_sessions/`. |
| Cover, video, and slide deck | Use the checked 16:9 [cover](../presentation/cover.png), final reviewed video, and ten-page [deck](../presentation/cutover-submission.pdf). |
| Additional Information | **This is a bounded SQLite rehearsal over synthetic single-table contracts and migration-statement boundaries; it does not model concurrent transactions, lock timing, crashes, or production databases. Codex built the evaluator and browser before kickoff; Bob authored the event repair and CI gate. See `docs/PROVENANCE.md` and the IDE task summaries. Render free may take about a minute to wake.** |

## Final project narrative for the form

A green build can still be a broken handover. During a rolling release, old and new workers share a database. Cutover executes both versions' SQL through every migration-statement boundary against disposable SQLite databases, then checks each acknowledged write against an independent ledger. A candidate can fail with a concrete replay: the old worker writes after a backfill but before synchronization exists, so the new reader sees stale data despite every completed-rollout check passing.

The browser lets a release engineer run curated examples or import a validated single-table contract and migration plan. It shows the failing SQL step, expected and observed row values, a timeline, and a downloadable JSON/Markdown/ZIP review packet. The CLI supplies the same deterministic evidence to an automated workflow. The public demo starts with an unsafe warehouse migration; **Load Bob's repair** reruns the actual event-period plan rather than selecting a prewritten passing reference.

IBM Bob IDE investigated the failing Parcel case through Cutover's read-only MCP tools. Its first bidirectional-trigger repair failed through recursion; the session preserves that attempt. Bob then saved a one-way bridge before backfill with explicit dual writes and adapted the plan to a separate Warehouse contract. Both saved plans passed 116/116 fresh bounded probes. Bob also built the GitHub pull-request gate. Three real PR runs retained full evidence: unsafe blocked 108/124, the safe reference passed 124/124, and a regressed plan blocked 100/116. Their downloaded artifacts and exact witnesses were independently replayed and mirrored publicly for signed-out judges.

Cutover is for backend and release engineers who need a counterexample before merging schema-changing code. The commercial hypothesis is a hosted per-repository CI review that attaches that counterexample to PRs; pricing and demand remain unvalidated. The current result is bounded to tested SQLite schedules, not a production deployment approval. Pre-event scaffolding and event-period Bob contributions are separated in `docs/PROVENANCE.md`.

## IBM Bob usage narrative for the form

IBM Bob IDE was the active developer in two event-period tasks on the provisioned hackathon account. In task `07a20bdb56f595035652c2e6732b2c53`, Bob used Cutover's read-only MCP inspection, diagnosis and rehearsal tools in a reference-withheld workspace. It found an old-worker write lost between backfill and trigger creation. A bidirectional-trigger candidate failed with recursive triggers; Bob kept that failure in its IDE history, revised to one-way synchronization before backfill plus explicit dual writes, and saved distinct Parcel and Warehouse candidate JSON files. Independent replay of each actual saved file passed 116/116 probes. In task `9aa1e2a2ae601940eb12f45bd6c2bf59`, Bob wrote the PR review helper, GitHub Actions workflow, focused tests and documentation. The gate distinguishes `verified_block` from `unverified`, preserves report and witness artifacts even when a PR is red, and shows exact coverage and differing values in its summary. Bob's local suite passed 67/67; independent checks and three live PR runs confirmed red, green and regressed-red behavior. The required task-session consumption PNGs, full IDE histories, source files, independent reports and PR artifacts are linked from the public repository. Codex-built pre-event scaffolding is disclosed separately.

## Pitch

Most application tests ask whether the new version works. During a rolling release, an older worker may still write to the same database. A migration can succeed and the new-version suite can pass while one worker sees stale data or a rollback loses visibility of a new write.

This workflow risk has an external engineering precedent: [GitLab documented a canary deployment that passed QA while the older production version failed to insert records after a schema migration](https://docs.gitlab.com/development/multi_version_compatibility/#downtime-on-release-features-between-canary-and-production-deployment). Its [migration guidance](https://docs.gitlab.com/development/database/avoiding_downtime_in_migrations/#renaming-columns) treats column renames as multi-stage work because older code can continue to use the original name. [Stripe's published online-migration sequence](https://stripe.com/blog/online-migrations) starts dual-writing before backfill. Cutover's late-bridge sample deliberately reverses that order to test the gap. These sources motivate the product; Cutover's measured results come only from its own fixed SQLite samples and do not replay either company's production migration.

Cutover makes that handover executable. A fixed old-version contract and a proposed new adapter run against disposable SQLite databases. An independent ledger checks each acknowledged write and the required target column; a candidate cannot pass by leaving the "new" adapter on the old column. When a schedule fails, the engineer gets the SQL, inputs, expected data and observed data. A local MCP interface lets IBM Bob investigate the counterexample and submit a revised candidate to the same evaluator.

[Atlas's migration analyzer](https://atlasgo.io/lint/analyzers) can flag destructive or backward-incompatible schema operations, including column renames. Cutover complements that category of check by executing the *old and new application's SQL* at each migration statement boundary and checking acknowledged values. That temporal replay is why it finds the late-bridge gap even when the completed migration passes; this is a distinction of the current samples, not a claim that other tools cannot model deployment timing.

The public browser covers two curated contracts and accepts a validated, user-supplied single-table SQLite contract with its own seed rows and test payloads; the local CLI accepts the same input. Both paths can export a review-ready Markdown timeline from the executed report. The bundled examples run 19 completed-rollout schedules with four string inputs each, plus old writes at every migration statement boundary. They detect direct schema breaks, stale data after a one-time backfill, and a late-bridge race that completed-rollout checks miss. The imported warehouse fixture reproduces the same structural failure on different SQL and domain values; it is not an independent customer incident. Results are bounded, reproducible evidence for review, not a claim of production safety. The intended user is a backend engineer shipping schema changes with long-lived workers.

The commercial hypothesis is an open local rehearsal tool paired with paid, per-repository CI checks that attach a counterexample to schema-changing pull requests. No pricing, willingness to pay, or market size has been validated. The next tests are interviews with release teams and a real repository adapter; the current two curated samples and CLI importer are not yet that service.

The actual Bob task records and bounded results are linked in [PROVENANCE.md](PROVENANCE.md); the narratives above are ready for the form after final media and link review.

## Demo script, target 3 minutes

The final nine-clip manifest pairs the pre-event Codex interface captures with reviewed IBM Bob IDE window frames, a fresh replay of Bob's saved candidate, and the public CI artifacts. The IDE segment is an edited montage of real event-window screenshots, not continuous recording.

- 0:00–0:18: Run Direct rename. The new-version baseline passes 8/8, while the full rollout passes only 24/92 and blocks on 68 probes.
- 0:18–0:42: Run Late bridge. All 76 completed-rollout probes pass, but 16 of 48 migration-window probes fail; the full result is 108/124.
- 0:42–1:04: Magnify the actual replay: the old write is acknowledged after backfill and before synchronization, then the new reader sees `4 Broad Street` instead of the latest `18 Marina Road`.
- 1:04–1:45: Show the actual Bob IDE task summaries, the failed recursive-trigger attempt, saved CI code and workflow, and Bob's 67/67 local tests.
- 1:45–2:12: Import and independently run Bob's saved Parcel candidate; show 116/116 and its executed migration-window replay.
- 2:12–2:33: Show actual GitHub CI artifacts: unsafe red at 108/124, safe green at 124/124, and a regressed red at 100/116.
- 2:33–2:50: Show the separately attributed, prewritten cross-record trap. Its migration windows pass 56/56, but the second write erases the first; the full browser result blocks at 100/132 and shows the exact expected and observed values.
- 2:50–3:00: End with the source and live demo, and name the bounded SQLite scope and untested concurrency/production-database work.

## Deck outline

1. Cover: a green build can still be a broken handover.
2. The release is a period when old and new workers share a database.
3. A late bridge passes completed-rollout checks but misses an old write between backfill and synchronization.
4. Fixed contracts, executed schedules, an independent ledger, and a replayable counterexample.
5. Controlled sample ablation: 0/3 unsafe patterns detected by the new-version baseline, 2/3 by completed-rollout checks, and 3/3 after migration windows. Not a customer benchmark or Bob result.
6. Validated browser and CLI import of a user-supplied warehouse contract, with its actual failing witness and separately attributed pre-event provenance.
7. Real Bob repair, shown with its task evidence and independently replayed candidate.
8. Backend/release engineers; CI report and PR review are the initial adoption path. A paid per-repository CI check is a revenue hypothesis, not observed demand.
9. Bob-built PR gate with its actual IDE task summary and linked unsafe-red, safe-green, regressed-red runs.

The final deck renderer accepts an optional `ci_evidence` object inside its observed Bob evidence JSON. It must contain `bob_ci_task_id`, the staged `bob_ci_summary_image`, and `run_receipts` with `unsafe`, `safe_reference`, and `regressed` paths. Save each private receipt using `work/verify-cutover-gh-run.py --receipt PATH` after it downloads and independently replays that actual GitHub run. `presentation/build_assets.py --evidence PATH` checks the receipts against the downloaded reports, reruns the evaluator, and confirms the three live GitHub conclusions before adding the CI page. The pre-event fixture plans are identified as controls, not Bob-authored repairs.
The final ten-page [PDF](../presentation/cutover-submission.pdf) has been rendered from the two reviewed task records and three independently verified PR receipts, then visually inspected.

## Final artifacts

- Public repository with MIT license and setup instructions: [github.com/josepha-mayo/cutover](https://github.com/josepha-mayo/cutover).
- Public working demo: [cutover-rehearsal.onrender.com](https://cutover-rehearsal.onrender.com/). Render free may take around a minute to wake after inactivity; verify it again before submission and recording.
- [16:9 PNG cover](../presentation/cover.png) generated. Recheck image requirements on the actual form.
- The final 180-second MP4 is staged at `public/demo.mp4` (12.9 MB, H.264/AAC); [watch page](https://cutover-rehearsal.onrender.com/watch) and signed-out playback must be checked after deployment. The reviewed [ten-page PDF deck](../presentation/cutover-submission.pdf) is ready.
- Both actual [Bob IDE task-summary PNGs and histories](../bob_sessions/) are in the public repository.
- Cutover solo team is active on lablab.ai; the live submission form is open during the event.
- After the event, complete the IBM/lablab feedback form to enter the 20 × $100 participant reward draw, provided the project was qualified and submitted by the deadline.
- Final descriptions/tags and submission confirmation.

## Official constraints checked on September 24

The event runs September 25–27, 2026. The [official live schedule](https://lablab.ai/ai-hackathons/ibm-bob-2-hackathon/live) gives kickoff September 25 at 16:00 West Africa Time and submission close September 27 at 16:00. The participant was approved and the event account was activated at kickoff. Aim to submit by September 27 at 12:00 West Africa Time, leaving four hours for upload or form recovery.

The [September event guide](https://lablab-ibm-bob-2-hackathon-guide.s3.us.cloud-object-storage.appdomain.cloud/index.html) requires Bob IDE to be a core component of a working developer-workflow prototype. Bob Shell is optional. Put a clearly named IDE task-session consumption-summary PNG for **every relevant task** in `bob_sessions/` in the final public repository. The IDE used the provisioned `ibm-coding-challenge-2` account in `us-east`; the personal trial was not used for qualifying work. This project uses synthetic SQLite records, not client, confidential, personal, or social-media data. The guide does not expressly approve pre-existing core work; Codex preparation and material event-period IDE work are attributed separately.

The event requires a developer-workflow prototype and evidence of IBM Bob's role. It judges technology application, presentation, business value and originality. The event page lists a $12,000 total prize pool: $10,000 for the top three projects and 20 × $100 participant rewards. The latter requires a qualified project by the deadline and a separate feedback form after the event. General lablab rules specify a public repository, online demo and presentation assets. The September 23 Codex prototype and the event-period Bob repair and CI gate are disclosed in [PROVENANCE.md](PROVENANCE.md).

Sources: [event](https://lablab.ai/ai-hackathons/ibm-bob-2-hackathon), [general pre-existing-code guidance](https://lablab.ai/guide/ai-hackathons), [participation terms](https://lablab.ai/terms-of-use#16-participation-terms), [submission guide](https://lablab.ai/ai-articles/hackathon-guidelines), [Bob MCP configuration](https://bob.ibm.com/docs/ide/configuration/mcp/mcp-in-bob).
