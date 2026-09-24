# Build and contribution provenance

This record separates preparation from the IBM Bob 2.0 Hackathon build. It is not evidence of an IBM Bob session. Update it with actual artifacts and commit hashes during the event; do not fill pending fields from plans or reference candidates.

## Pre-event baseline — September 23, 2026

The public source beginning at commit `c90cb2580284415ec18a1265cbb3edb4f017eab8` was built with Codex before the September 25 kickoff. It includes the deterministic SQLite rehearsal engine, fixed sample contracts, reference candidates, independent ledger, browser UI, HTTP and CLI interfaces, MCP server and Bob configuration, tests, public demo, and draft presentation assets. The passing window-safe reference is prewritten and cannot be represented as Bob's output. The prepared reference-withheld sibling workspace is also pre-event setup, not a Bob contribution.

On September 24, after the user approved the free-trial Shell license and a short-lived inference key, IBM Bob Shell completed three capped **pre-event readiness checks**. A read-only task (`2387d0973a2ae145093b2409f686b3a4`) actually called `mcp__cutover__inspect_release` against Parcel through the configured project server; the full transcript is retained privately. The signed-in IDE listed these Shell tasks under All workspaces. No Bob-authored repair or qualifying event-period development has occurred. Do not count these checks as hackathon work.

The later presentation finalizer, demo shot list, local neural narration renderer, MP4 assembler, validated custom-contract CLI and browser importer, warehouse fixture, and Markdown review renderer are pre-event Codex preparation too. The narration and clip templates deliberately reject their pending Bob evidence, and no final MP4 has been produced. Record the last pre-kickoff commit hash here when the event opens; do not attribute any pre-kickoff commits to Bob.

The v0.2.3 evaluator change at commit `a32866e02f3199e8fa9118de5a75bf6c45610ce5` is also pre-event Codex work. It rejects a new reader that returns old-column values while only touching the target column in a no-op expression. The reference-withheld workspace prepared from that commit is a rehearsal environment, not a Bob-authored candidate or task session.

The v0.2.4 evaluator change at commit `980d12b6ea5fe5a96d7897249a03d33c2ec4ebb4` is pre-event Codex work as well. It checks new updates and inserts on a trigger-free snapshot, preventing a plan from passing only because an old-column trigger carries the value to the target. The reference-withheld workspace from this commit remains preparation, not event-period Bob work.

The [event page](https://lablab.ai/ai-hackathons/ibm-bob-2-hackathon) describes a 48-hour build on September 25–27, advertises Bob access at kickoff, asks for Bob-assisted files and task-summary screenshots, and encourages participants to get a head start. It does not explicitly define what pre-existing code is allowed. [lablab's general AI hackathon guide](https://lablab.ai/guide/ai-hackathons) says prior non-AI scaffolding is generally allowed while the core AI-powered functionality is usually built during the event, and directs participants to check event-specific rules. This general guide is not event-specific approval for Cutover.

## Event-period evidence gate — pending

At kickoff, check the published brief and any event-specific rules. If they restrict pre-existing code more tightly, follow those rules before claiming eligibility or submitting. Record the exact rule source and decision here.

The proposed event work is for IBM Bob to diagnose the deliberately failing late-bridge release through Cutover's MCP tools, author and save its own candidate repair, then build and verify a CI review gate that fails unsafe migration PRs while retaining evidence. The [task brief](BOB_TASK.md) defines requested behavior; it is not proof of completion. A material Bob contribution must be visible in an actual Bob session and in inspectable files created or changed during the event. Do not treat merely calling Bob, opening the prepared UI, selecting the prewritten passing candidate, or using the pre-event import and review features as the core AI contribution.

| Evidence | Record after it exists |
| --- | --- |
| Kickoff rules | Source URL or screenshot, time checked, any pre-existing-code limit |
| Bob access | Version, session/task identifier if shown, first-use time |
| Diagnosis | Original prompt, executed MCP calls, actual failing replay, Bob's analysis |
| Candidate repair | Bob-written file and hash, failed attempts retained, independent CLI/browser replay |
| Product extension | Bob-assisted changed files, before/after commits, tests and observed output |
| Task records | Actual Bob task-summary captures, IDE-exported Markdown histories where required, and their repository paths under `bob_sessions/` |
| Presentation | Final video/deck show only observed Bob actions and bounded results |

Before submission, compare the final Git diff against this baseline, review each Bob-attributed file and summary, rerun the reported candidate with the fixed evaluator, and make the source, demo, video, deck, and form tell the same story. If Bob cannot produce a passing repair, preserve that result and show only what it did achieve. A passing reference plan is not a substitute.

The deck builder accepts real artifacts only after the session. Save a legible, tightly cropped Bob task-summary screenshot and Bob-written candidate JSON in the project, then generate the full independent report with `python -m cutover --case parcel --plan PATH_TO_CANDIDATE --output PATH_TO_REPORT`. Create a manifest with `bob_task_id`, `session_time_utc`, `bob_summary_image`, `bob_candidate`, `candidate_report`, and `bob_contribution` (paths are project-relative), and run `python presentation/build_assets.py --evidence PATH --output presentation/cutover-submission.pdf` with the presentation Python environment. The builder checks that the image and files exist, the session time falls within the advertised event window, and the later full report matches the exact candidate and current evaluator source. It then reruns the candidate in a fresh bounded worker and compares the complete deterministic probe results. These checks prevent accidental mismatch or stale evidence; they do not prove authorship. Inspect the actual Bob session and final PDF before submitting.
