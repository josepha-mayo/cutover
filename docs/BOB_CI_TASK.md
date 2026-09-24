# Event-period Bob CI task — prompt, not completed work

When creating the GitHub Actions file, write to **exactly**
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
