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

After saving the repair, open the full Cutover project in normal Bob Agent mode for a separate development task: add a review-ready Markdown report with one failing replay, a migration-step timeline, exact coverage and untested boundaries. Validate it against the fixed JSON report and test it with both a failing and a passing candidate. This is a next milestone, not present functionality. Do not silently weaken the evaluator.

## Recording sequence

Show a real failing browser run, switch to the real Bob session for the diagnosis/repair, return to Cutover, import the candidate Bob actually saved, rerun, open a successful rollback replay, then show the exact limitations. Preserve unsuccessful Bob attempts as part of the evidence.
