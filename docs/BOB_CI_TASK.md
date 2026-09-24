# Event-period Bob CI task — prompt, not completed work

Implement and locally exercise `ci/review_gate.py` first. Then create the
GitHub Actions file at **exactly**
`.github/workflows/cutover-review.yml`. The mode rejects other workflow
filenames, including `.github/workflows/pr-gate.yml`. If your file-writing
tool reports a rejected path, correct that path and retry; a final explanation
without a saved workflow is incomplete.

Use this file only after the September 25 kickoff in a fresh IBM Bob task using
the **Cutover CI builder** mode. The evaluator, imported warehouse fixture,
`cutover.audit_report`, and `--bundle` export were written before the event by
Codex. They are available tools, not Bob contributions.

Build a reusable GitHub Actions pull-request gate for a repository with a
checked-in SQLite contract JSON and candidate plan JSON. Invoke the existing
Cutover CLI in its bounded worker. Run `cutover.audit_report` against the same
inputs and exported report. An executed unsafe candidate must fail the check,
but still retain its JSON evidence, Markdown review, and review ZIP as
downloadable artifacts. A passing candidate must produce a green check and
the same artifacts. Invalid input, timeout, or report mismatch must fail as
**unverified**, never as a verified unsafe verdict.

Make a small `ci/review_gate.py` the entry point. Have it invoke the CLI and
audit as separate subprocesses with explicit timeouts, capture both return
codes, retain `work/pr-summary.md`, append that summary to
`GITHUB_STEP_SUMMARY` when set, and exit 0 only for a verified pass.
Keep the Actions YAML to checkout, Python setup, one helper invocation, and an
`if: always()` evidence upload. A failed helper step must still reach the upload.
Do not use `continue-on-error`, a shell pipeline, or a GitHub step's outcome to
infer whether an executed candidate was safe. A pre-event disposable Bob Shell
probe generated a workflow that lost the blocked CLI/audit exit codes through
those patterns; that probe is not event work and its output is not part of this
repository.

This repository is Python, not Node. Before implementing, inspect
`cutover/__main__.py`, `cutover/audit_report.py`, and the current workflow. The
commands to compose are `python -m cutover --contract
examples/warehouse/contract.json --plan ci/candidate.json --output ...
--markdown ... --bundle ...` and `python -m cutover.audit_report --report ...
--plan ci/candidate.json --contract examples/warehouse/contract.json`.
The first exits 0 for a pass and 1 for a block; the independent audit exits
0 for a verified pass, 1 for a verified block, and 2 for unverified evidence.
Classify only the pair `(CLI 0, audit 0)` as verified pass and `(CLI 1, audit
1)` as verified block; every other pair is unverified. Never infer a verified
block from the first command alone. A
timeout or missing report is unverified. Preserve generated artifacts on every
verdict with an unconditional upload step, then fail the job for both blocked
and unverified outcomes. The job summary should make those outcomes visibly
different.

Use `examples/warehouse/contract.json` and `ci/candidate.json` as the default
checked-in inputs. The candidate will be staged before this task from Bob's
separate, independently assessed Warehouse repair if it verifies, or from a
clearly labeled pre-event Warehouse reference plan if it does not. A Parcel
plan is not valid for the Warehouse contract. Treat both
input files as read-only; never adjust the plan or contract to make the gate
green. Put the paths in obvious workflow variables so another repository can
replace them. Trigger on `pull_request` with read-only repository permissions,
no secrets, and no privileged `pull_request_target` execution. Do not hide a
blocked verdict with `continue-on-error`.

Put the exact first observed failing probe, expected and actual values, plan
hash, contract hash, and artifact link in the GitHub job summary when blocked.
For a pass, show the exact coverage and hashes without implying production
safety. Keep the workflow minimal enough for another repository to copy; write
setup instructions in `docs/CI.md`. You may write only the workflow named
`.github/workflows/cutover-review.yml`, Python or Markdown helper files under
`ci/`, a focused `tests/test_ci_gate.py`, and `docs/CI.md`. Do not edit the
engine, fixtures, existing tests, contract, or candidate. Do not push or
publish anything.

Use the read-only Cutover MCP tools if useful to inspect a real blocked
warehouse replay. Save your actual files and report which commands or checks
you could not run in this scoped mode. Independent verification will then
exercise three controlled GitHub runs: a late-bridge candidate that blocks
with retained artifacts, a safe candidate that passes 124/124, and a plan
with one synchronization direction removed that blocks again. Any failed
attempts will be retained as event evidence rather than hidden.
Before the GitHub runs, execute your helper locally with each of those three
checked-in fixture plans and inspect its exit, summary, and retained files.
Check a malformed plan too: it must be unverified, not a verified block.
If the task budget ends before the workflow and tests are complete, leave the
actual helper and partial files in place and state precisely what remains;
the next IDE task can continue from those files with a separate summary PNG.
