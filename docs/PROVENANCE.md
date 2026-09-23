# Build and contribution provenance

This record separates preparation from the IBM Bob 2.0 Hackathon build. It is not evidence of an IBM Bob session. Update it with actual artifacts and commit hashes during the event; do not fill pending fields from plans or reference candidates.

## Pre-event baseline — September 23, 2026

The public source at commit `c90cb2580284415ec18a1265cbb3edb4f017eab8` was built with Codex before the September 25 kickoff. It includes the deterministic SQLite rehearsal engine, fixed sample contracts, reference candidates, independent ledger, browser UI, HTTP and CLI interfaces, MCP server and Bob configuration, tests, public demo, and draft presentation assets. The MCP server has been tested with an SDK client, but there has been **no IBM Bob host session or Bob-authored repair**. The passing window-safe reference is prewritten and cannot be represented as Bob's output. The prepared reference-withheld sibling workspace is also pre-event setup, not a Bob contribution.

The [event page](https://lablab.ai/ai-hackathons/ibm-bob-2-hackathon) describes a 48-hour build on September 25–27, advertises Bob access at kickoff, asks for Bob-assisted files and task-summary screenshots, and encourages participants to get a head start. It does not explicitly define what pre-existing code is allowed. [lablab's general AI hackathon guide](https://lablab.ai/guide/ai-hackathons) says prior non-AI scaffolding is generally allowed while the core AI-powered functionality is usually built during the event, and directs participants to check event-specific rules. This general guide is not event-specific approval for Cutover.

## Event-period evidence gate — pending

At kickoff, check the published brief and any event-specific rules. If they restrict pre-existing code more tightly, follow those rules before claiming eligibility or submitting. Record the exact rule source and decision here.

The proposed event work is for IBM Bob to diagnose the deliberately failing late-bridge release through Cutover's MCP tools, author and save its own candidate repair, and then build a review-ready Markdown report path in the full project. The [task brief](BOB_TASK.md) defines the requested behavior; it is not proof of completion. A material Bob contribution must be visible in an actual Bob session and in inspectable files created or changed during the event. Do not treat merely calling Bob, opening the prepared UI, or selecting the prewritten passing candidate as the core AI contribution.

| Evidence | Record after it exists |
| --- | --- |
| Kickoff rules | Source URL or screenshot, time checked, any pre-existing-code limit |
| Bob access | Version, session/task identifier if shown, first-use time |
| Diagnosis | Original prompt, executed MCP calls, actual failing replay, Bob's analysis |
| Candidate repair | Bob-written file and hash, failed attempts retained, independent CLI/browser replay |
| Product extension | Bob-assisted changed files, before/after commits, tests and observed output |
| Required screenshots | Actual Bob task-summary captures and their local paths |
| Presentation | Final video/deck show only observed Bob actions and bounded results |

Before submission, compare the final Git diff against this baseline, review each Bob-attributed file and summary, rerun the reported candidate with the fixed evaluator, and make the source, demo, video, deck, and form tell the same story. If Bob cannot produce a passing repair, preserve that result and show only what it did achieve. A passing reference plan is not a substitute.
