# Actual Bob repair task

The purpose of this session is to obtain a genuine IBM Bob contribution. These are instructions for the future session, not a transcript or completed result.

From a clean committed source project, run `python prepare_bob_session.py --python PATH_TO_MCP_PYTHON`. Open the printed reference-withheld sibling workspace in IBM Bob, confirm **Use MCP Servers** is enabled and the `cutover` project server is listed in [Bob's MCP settings](https://bob.ibm.com/docs/ide/configuration/mcp/mcp-in-bob), and choose the Cutover release engineer mode. The fixed evaluator is copied byte-for-byte, while prewritten passing plans and presentation notes are omitted. Begin a new task:

> Rehearse the Parcel release using inspect_release and diagnose_reference with reference=late_bridge. The late bridge passes all 76 completed-rollout probes yet fails migration-window probes. Diagnose the shortest failing replay and propose your own migration and new SQL adapter that preserve the old application contract, inserted records and rollback reads, including old writes between migration statements. Use rehearse_candidate to test each proposal. Do not change the fixed old contract, seed records, evaluator, schedule generator, or test assertions. Save your own proposed plan to work/bob-candidate.json and explain observed failures and repair in work/bob-repair.md. Report exact final coverage and untested boundaries. Do not use the bundled window-safe bridge as proof of your own repair work.

## Evidence to retain

- Actual Bob version and displayed task/session identifier, if available.
- Original task prompt and timestamp.
- Screenshots of Bob's executed tool calls and its actual task summary.
- Every candidate it submits, including failures.
- The generated `SESSION_MANIFEST.json` with source commit and evaluator hash.
- JSON reports from rerunning its final candidate in the full source project's CLI and browser.
- Which files Bob wrote or changed, with an honest separation from pre-event preparation.

## A meaningful extension if the first repair succeeds quickly

After saving the repair, open the full Cutover project in normal Bob Agent mode for a separate development task. If repair is still blocked after a focused attempt, retain that failure and move to this independent build task before the recording window; do not present an unsolved candidate as a repair. Give Bob this concrete build brief:

> Add a `--markdown PATH` option to `python -m cutover` that writes a review-ready Markdown report from the **same executed report object** used for the JSON verdict. Include the case, candidate name, exact baseline/completed-rollout/migration-window counts, plan/contract/suite/engine hashes, and the tested limitations. For a blocked candidate, include the shortest observed failing replay as an ordered migration/write/read timeline with executed SQL, inputs, expected values and observed values. For a passing candidate, include one actual passing migration-window replay and state that passing is bounded to this suite. Render arbitrary candidate SQL as safe Markdown code blocks. Add focused tests for both outcomes. Keep the fixed contract, oracle, schedules and evaluator unchanged; do not hardcode the reference candidates' names or counts into the renderer.

Acceptance: run `python -m cutover --reference late_bridge --output work/late.json --markdown work/late-review.md` and expect the existing blocked exit code plus a report containing the stale-data witness. Run `python -m cutover --reference bridge --output work/safe.json --markdown work/safe-review.md` and expect the existing pass exit code plus a passing migration-window replay. Compare each Markdown file with the JSON report from the same run, then run the full test suite and CI. Capture Bob's actual task summary, changed files and any failed attempts. This is a next milestone, not present functionality; the CLI does not yet support `--markdown`.

## Recording sequence

Show a real failing browser run, switch to the real Bob session for the diagnosis/repair, return to Cutover, import the candidate Bob actually saved, rerun, open a successful rollback replay, then show the exact limitations. Preserve unsuccessful Bob attempts as part of the evidence.
