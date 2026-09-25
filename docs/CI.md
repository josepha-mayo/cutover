# Cutover CI review gate

This document explains how to set up and interpret the automated pull-request
gate that verifies each checked-in migration candidate against its own SQLite
contract. The workflow runs Bob's original gate independently for Warehouse
and Parcel. Codex added the two-case workflow matrix after Bob's task;
`ci/parcel-candidate.json` is an exact copy of Bob's saved Parcel plan.
`ci/parcel-contract.json` copies the bundled synthetic Parcel contract
and makes its four previously implicit test payloads explicit for the
imported-contract CLI path. No evaluator or expected result was changed.

---

## How it works

The gate runs two independent steps and classifies the result from their
combined exit codes:

| CLI exit | Audit exit | Classification |
| --- | --- | --- |
| 0 | 0 | `verified_pass` |
| 1 | 1 | `verified_block` |
| anything else | anything else | `unverified` |

**Step 1 — Cutover CLI** (`python -m cutover`)  
Executes the candidate migration against disposable in-memory SQLite databases,
checks every rollout and migration-window probe against an independent ledger,
and writes `report.json`, `review.md`, and `review.zip`.  Exits 0 for pass,
1 for block.

**Step 2 — Independent audit** (`python -m cutover.audit_report`)  
Re-runs the same candidate from the checked-in inputs and compares the fresh
replay against the exported `report.json`.  Exits 0 for verified pass, 1 for
verified block, 2 for unverified evidence (mismatch, timeout, or error).

Both commands run as separate subprocesses with explicit 120-second timeouts.
A timeout or process error makes the result `unverified`, never
`verified_block`.

`ci/review_gate.py` retains up to five files in `--output-dir`; the verdict and
summary are written even when malformed input prevents a rehearsal:

| File | When written | Contents |
| --- | --- | --- |
| `report.json` | CLI succeeds | Full executed evidence report |
| `review.md` | CLI succeeds | Review-ready Markdown from the report |
| `review.zip` | CLI succeeds | ZIP with inputs, evidence, and review |
| `summary.md` | Always | Human-readable verdict with hashes and coverage |
| `verdict.json` | Always | Machine-readable verdict with exit codes |

`verdict.json` always contains `classification`, `cli_exit`, `audit_exit`,
`contract_hash`, and `plan_hash`.  For a `verified_block` it also contains
`witness_id` and `witness_failure` (the exact `expected`/`actual` row map from
the first failing probe).

---

## GitHub Actions workflow

The workflow is at [`.github/workflows/cutover-review.yml`](../.github/workflows/cutover-review.yml).
It triggers on `pull_request` with read-only repository permissions and no
secrets. Its matrix runs two independent jobs, one per contract/plan pair.
Each job has exactly four steps:

1. `actions/checkout@v4`
2. `actions/setup-python@v5` (Python 3.12)
3. **Run Cutover review gate** — invokes `ci/review_gate.py`; fails the step
   for `verified_block` and `unverified` outcomes
4. **Upload review evidence** — `if: always()` so each case's uniquely named
   artifacts are preserved even when its gate step fails

The helper uses only the Python standard library, so no `pip install` step is
needed.

### Input paths

Add one entry per checked-in release to `strategy.matrix.include`:

```yaml
strategy:
  fail-fast: false
  matrix:
    include:
      - case: Warehouse
        slug: warehouse
        contract: examples/warehouse/contract.json
        plan: ci/candidate.json
      - case: Parcel
        slug: parcel
        contract: ci/parcel-contract.json
        plan: ci/parcel-candidate.json
```

Add or replace paths to adapt the workflow for another repository. The
contract and plan files are read-only inputs. One verified block makes its
case check red while other cases still run and retain their evidence.

---

## Reading a blocked result

When the gate exits 1 (`verified_block`), the job summary shows:

- `report.plan_hash` and `report.contract_hash` — the hashes embedded in the
  executed evidence, not raw file checksums
- `report.passed / report.total` — exact probe coverage (e.g. `108/124`)
- `witness.id` — the identity of the first failing probe
- The first row key where `expected` ≠ `actual`, with both exact values

Example blocked summary excerpt:

```
**Coverage:** 108/124 probes passed.
**Probe:** `window_write_after_2-0`
**First differing value (row `11`):**
| | Value |
| Expected | `R-07` |
| Actual   | `A-01` |
```

Download `report.json` and `review.md` from the artifact for the full witness
trace showing exactly which migration-window interleaving caused the failure.

---

## Reading a passing result

When the gate exits 0 (`verified_pass`), the job summary shows the same
hashes and `passed/total` coverage and appends:

> **A pass is bounded to this suite; it is not a deployment approval.**

---

## Reading an unverified result

Exit code 2 means the gate could not produce a definitive verdict.  Common
causes: malformed input JSON, CLI timeout, or a CLI/audit exit-code pair that
does not correspond to a known outcome.  Check the `audit_stderr` section of
`summary.md` and the `verdict.json` fields (`cli_exit`, `audit_exit`) to
diagnose.  A malformed plan is always `unverified`, never `verified_block`.

---

## Running the gate locally

```bash
python ci/review_gate.py \
  --contract examples/warehouse/contract.json \
  --plan ci/candidate.json \
  --output-dir work/ci-review
echo "exit: $?"
cat work/ci-review/verdict.json
```

Substitute `--plan` to test any fixture:

| Plan | Expected outcome |
| --- | --- |
| `examples/warehouse/bridge.json` | `verified_pass` (124/124) |
| `examples/warehouse/late_bridge.json` | `verified_block` (108/124) |
| `ci/candidate.json` | `verified_pass` (checked-in candidate) |

---

## Running the focused tests

```bash
python -m pytest tests/test_ci_gate.py -v
```

Six tests cover Warehouse and Parcel `verified_pass`, `verified_block` (with
coverage and witness assertions), `unverified` from malformed JSON, and
`unverified` from a missing file. They do not modify any fixture or contract.
