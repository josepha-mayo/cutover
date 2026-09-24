# Submission preparation — not submitted

Working title: **Cutover: Rehearse the Release**

Short description (draft): Cutover replays old and new SQL through schema migrations, exposes lost-write windows, and gives IBM Bob an executable counterexample to investigate.

Provisional form fields: demo platform **Render**; application URL **https://cutover-rehearsal.onrender.com/**; code URL **https://github.com/josepha-mayo/cutover**. Candidate tags are **IBM Bob 2.0**, **developer tools**, **testing**, **DevOps**, **database migrations**, and **MCP**, subject to the form's actual choices. Keep the long description below as the base, then replace the Bob placeholder with observed task ID, files, tool calls, candidate outcome, and independently replayed counts. Do not paste a pending or planned outcome into the final form.

The [general lablab submission guide](https://lablab.ai/ai-articles/hackathon-guidelines) lists a title of at most 50 characters, a summary of at most 255 characters, a long description of at least 100 words, cover/video fields, repository/demo links, technologies, and a separate **Additional Information** field. Recheck the actual September form at kickoff; the general guide does not settle event-specific fields or rules.

| Field | Prepared copy or gate |
| --- | --- |
| Title | **Cutover: Rehearse the Release** |
| Summary | **Cutover replays old and new SQL through schema migrations, exposes lost-write windows, and gives IBM Bob an executable counterexample to investigate.** (149 characters) |
| Long description | Use the pitch below, then add only the observed event-period Bob contribution and its independently measured outcome. |
| Main track and technologies | Choose the actual event track at kickoff. Name IBM Bob 2.0, MCP, Python, SQLite, JavaScript, and Render only where the form permits them. |
| Cover, video, and slide deck | Use the checked 16:9 cover. Add the final reviewed video URL and evidenced PDF only after the real Bob session; verify upload/link behavior in the live form. |
| Additional Information | **This is a bounded SQLite rehearsal over fixed sample contracts and migration-statement boundaries; it does not model concurrent transactions, lock timing, or production databases. The pre-event deterministic baseline is documented in `docs/PROVENANCE.md`. [PENDING: describe and link the actual event-period Bob task history, candidate attempts, and independent replay.] The Render free demo may take about a minute to wake.** Replace the bracketed text and recheck every clause and artifact link before submitting. |

## Pitch

Most application tests ask whether the new version works. During a rolling release, an older worker may still write to the same database. A migration can succeed and the new-version suite can pass while one worker sees stale data or a rollback loses visibility of a new write.

This workflow risk has an external engineering precedent: [GitLab documented a canary deployment that passed QA while the older production version failed to insert records after a schema migration](https://docs.gitlab.com/development/multi_version_compatibility/#downtime-on-release-features-between-canary-and-production-deployment). Its [migration guidance](https://docs.gitlab.com/development/database/avoiding_downtime_in_migrations/#renaming-columns) treats column renames as multi-stage work because older code can continue to use the original name. [Stripe's published online-migration sequence](https://stripe.com/blog/online-migrations) starts dual-writing before backfill. Cutover's late-bridge sample deliberately reverses that order to test the gap. These sources motivate the product; Cutover's measured results come only from its own fixed SQLite samples and do not replay either company's production migration.

Cutover makes that handover executable. A fixed old-version contract and a proposed new adapter run against disposable SQLite databases. An independent ledger checks each acknowledged write and the required target column; a candidate cannot pass by leaving the "new" adapter on the old column. When a schedule fails, the engineer gets the SQL, inputs, expected data and observed data. A local MCP interface lets IBM Bob investigate the counterexample and submit a revised candidate to the same evaluator.

[Atlas's migration analyzer](https://atlasgo.io/lint/analyzers) can flag destructive or backward-incompatible schema operations, including column renames. Cutover complements that category of check by executing the *old and new application's SQL* at each migration statement boundary and checking acknowledged values. That temporal replay is why it finds the late-bridge gap even when the completed migration passes; this is a distinction of the current samples, not a claim that other tools cannot model deployment timing.

The public browser covers two curated contracts and accepts a validated, user-supplied single-table SQLite contract with its own seed rows and test payloads; the local CLI accepts the same input. Both paths can export a review-ready Markdown timeline from the executed report. The bundled examples run 19 completed-rollout schedules with four string inputs each, plus old writes at every migration statement boundary. They detect direct schema breaks, stale data after a one-time backfill, and a late-bridge race that completed-rollout checks miss. The imported warehouse fixture reproduces the same structural failure on different SQL and domain values; it is not an independent customer incident. Results are bounded, reproducible evidence for review, not a claim of production safety. The intended user is a backend engineer shipping schema changes with long-lived workers.

The commercial hypothesis is an open local rehearsal tool paired with paid, per-repository CI checks that attach a counterexample to schema-changing pull requests. No pricing, willingness to pay, or market size has been validated. The next tests are interviews with release teams and a real repository adapter; the current two curated samples and CLI importer are not yet that service.

**Update the Bob paragraph to describe only the session that was actually performed before publishing. No real Bob repair has been captured yet.**

## Demo script, target 3 minutes

The [shot-by-shot recording plan](../presentation/recording-plan.md) ties each clip to the required on-screen evidence and leaves the Bob result pending until an actual session.

- 0:00–0:18: Run Direct rename. The new-version baseline passes 8/8, while the full rollout passes only 24/92 and blocks on 68 probes.
- 0:18–0:42: Run Late bridge. All 76 completed-rollout probes pass, but 16 of 48 migration-window probes fail; the full result is 108/124.
- 0:42–1:04: Magnify the actual replay: the old write is acknowledged after backfill and before synchronization, then the new reader sees `4 Broad Street` instead of the latest `18 Marina Road`.
- 1:04–1:45: Show the real Bob task, diagnostic tool calls, candidate files, and task summary. Describe actual attempts, including any failures, without inventing a repair.
- 1:45–2:12: Import and independently run Bob's saved candidate. State only its observed counts and show a migration-window replay.
- 2:12–2:33: Show the pre-event browser import of the warehouse contract and its blocked Markdown review, clearly attributed to Codex preparation; show the event-period CI gate only if Bob actually built and verified it.
- 2:33–2:50: Show the separately attributed, prewritten cross-record trap. Its migration windows pass 56/56, but the second write erases the first; the full browser result blocks at 100/132 and shows the exact expected and observed values.
- 2:50–3:00: End with the source and live demo, and name the bounded SQLite scope and untested concurrency/production-database work.

## Deck outline

1. Cover: a green build can still be a broken handover.
2. The release is a period when old and new workers share a database.
3. A late bridge passes completed-rollout checks but misses an old write between backfill and synchronization.
4. Fixed contracts, executed schedules, an independent ledger, and a replayable counterexample.
5. Controlled sample ablation: 0/3 unsafe patterns detected by the new-version baseline, 2/3 by completed-rollout checks, and 3/3 after migration windows. Not a customer benchmark or Bob result.
6. Validated browser and CLI import of a user-supplied warehouse contract, with its actual failing witness and separately attributed pre-event provenance.
7. Real Bob contribution, shown only with task evidence and an independently replayed candidate.
8. Backend/release engineers; CI report and PR review are the initial adoption path. A paid per-repository CI check is a revenue hypothesis, not observed demand.

## Final artifacts

- Public repository with MIT license and setup instructions: [github.com/josepha-mayo/cutover](https://github.com/josepha-mayo/cutover).
- Public working demo: [cutover-rehearsal.onrender.com](https://cutover-rehearsal.onrender.com/). Render free may take around a minute to wake after inactivity; verify it again before submission and recording.
- [16:9 PNG cover](../presentation/cover.png) generated. Recheck image requirements on the actual form.
- Recorded MP4 demo and final PDF slide deck. A local eight-page PDF draft exists, with its Bob slide clearly marked pending and a separately attributed pre-event custom-contract slide. Replace the Bob slide with real session evidence before submission. The general guide asks for a video link, under 300 MB and within five minutes; check the final export and signed-out playback of its public link, then verify the actual event form accepts it.
- Actual Bob task-summary screenshots and Bob-assisted files.
- Cutover solo team created on lablab.ai; submission form remains unavailable until the active phase.
- After the event, complete the IBM/lablab feedback form to enter the 20 × $100 participant reward draw, provided the project was qualified and submitted by the deadline.
- Final descriptions/tags and submission confirmation.

## Official constraints checked on September 24

The event runs September 25–27, 2026. The [official live schedule](https://lablab.ai/ai-hackathons/ibm-bob-2-hackathon/live) gives kickoff September 25 at 16:00 West Africa Time and submission close September 27 at 16:00. A September 24 organizer email says **registration closes September 24 at 22:00 CEST**, earlier than the live dashboard wording. The September 23 approval email confirms this participant was approved; the earlier registration email said only applicants who completed its mandatory survey would be approved. The separate hackathon Bob-account invitation is expected at kickoff, not yet received.

The [September event guide](https://lablab-ibm-bob-2-hackathon-guide.s3.us.cloud-object-storage.appdomain.cloud/index.html) requires Bob IDE to be a core component of a working developer-workflow prototype. Bob Shell is optional. Put a clearly named IDE task-session consumption-summary PNG for **every relevant task** in `bob_sessions/` in the final public repository. The event-provisioned Bob account is `ibm-coding-challenge-uat` in `us-east` with 40 Bobcoins; switch away from the personal trial before qualifying work. This project uses synthetic SQLite records, not client, confidential, personal, or social-media data. The guide does not state that pre-event core work is allowed, so keep Codex preparation explicitly attributed and make the event-period IDE contribution material and verifiable.

The event requires a developer-workflow prototype and evidence of IBM Bob's role. It judges technology application, presentation, business value and originality. The current rendered event page lists a $12,000 total prize pool: $10,000 for the top three projects and 20 × $100 participant rewards. The reward requires a qualified project by the deadline and a feedback form after the event. It also says submissions must be original and MIT-compliant. General lablab rules specify a public repository, online demo and presentation assets. The event page encourages preparation but gives no explicit event-specific permission for existing code. lablab's general guide says prior non-AI scaffolding is generally allowed while core AI functionality is usually built during the event; it says to check event-specific rules. The September 23 Codex prototype is disclosed in [PROVENANCE.md](PROVENANCE.md). Confirm kickoff rules and build a material, evidenced Bob contribution during the event before submission. Access to Bob is advertised for kickoff.

Sources: [event](https://lablab.ai/ai-hackathons/ibm-bob-2-hackathon), [general pre-existing-code guidance](https://lablab.ai/guide/ai-hackathons), [participation terms](https://lablab.ai/terms-of-use#16-participation-terms), [submission guide](https://lablab.ai/ai-articles/hackathon-guidelines), [Bob MCP configuration](https://bob.ibm.com/docs/ide/configuration/mcp/mcp-in-bob).
