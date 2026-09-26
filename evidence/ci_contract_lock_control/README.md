# Keep the test contract fixed while repairing SQL

These are downloaded artifacts from [control PR #13](https://github.com/josepha-mayo/cutover/pull/13) and
[GitHub run 36215341123](https://github.com/josepha-mayo/cutover/actions/runs/36215341123). The original contract, changed
contract and expected outcomes were committed before the run. Every unsafe
case used the **same SQL and new-worker adapters**; only the seed record IDs
changed. The repaired case uses the bundled bridge reference, not a new Bob repair.

| Control | Contract lock | Actual result |
| --- | --- | --- |
| Unsafe SQL, original records | Matched | Verified block, 100/132 |
| Same unsafe SQL, changed record IDs | Not configured | Pass on changed tests, 132/132 |
| Same unsafe SQL and changed IDs | Original hash required | Unverified; SQL not executed |
| Repaired SQL, original records | Matched | Verified pass, 124/124 |

The second result is a bounded pass on different test inputs, **not a repair**.
The lock prevents that changed contract from silently replacing the reviewed one.
It checks the schema, old-worker adapters, seed records, payloads and remaining
contract fields; JSON formatting and key order do not affect the hash.

The expected block and unverified Action steps actually failed. The control
workflow uses `continue-on-error` so a following assertion can check their
outputs and retained verdicts; the overall control jobs pass only when those
prospectively stated outcomes match. This is a synthetic project test, not
external adoption, production safety evidence, or another Bob IDE task.

## Inspect the exact evidence

- [Original unsafe result](unsafe-original-locked/summary.md), [verdict](unsafe-original-locked/verdict.json), [packet](unsafe-original-locked/review.zip).
- [Changed tests without a lock](unsafe-changed-unlocked/summary.md), [verdict](unsafe-changed-unlocked/verdict.json), [packet](unsafe-changed-unlocked/review.zip).
- [Changed contract stopped by the lock](unsafe-changed-locked/summary.md), [verdict](unsafe-changed-locked/verdict.json). No report or review ZIP was produced because SQL was not executed.
- [Actual repair on the original contract](repair-original-locked/summary.md), [verdict](repair-original-locked/verdict.json), [packet](repair-original-locked/review.zip).
- [Original contract](inputs/original.json), [changed contract](inputs/changed.json), [unchanged unsafe SQL](inputs/unsafe.sql), [repair SQL](inputs/safe.sql), [prospective expectations](inputs/expected.json).

All three executed review ZIPs passed independent replay after download. Their
plans were checked against the actual SQL and adapters at the GitHub checkout,
and their contract hashes matched those exact checkout inputs. Both unsafe
executed packets share plan hash `862e5029121fdbd47f341daee93015d55071bbeb35499bc89810833ac70e1867`.

- PR head: `97431e04441942d243a19e8a55006ea543855561`
- Actual GitHub merge checkout: `5ffa63d5ca6aac4762cccb35c6415b3c3c256e94`
- Pinned public Action: `65984c8efd007e2d50d6beaf5afbdac500ec690b`
- [Every mirrored artifact and input SHA-256](manifest.json)

The bytes of the downloaded artifacts are preserved. The mirror is not a signed
attestation. Lock and workflow changes still need repository review rules;
deliberately replacing the expected hash changes the agreement. Do not compute
the expected hash from the proposed contract inside the pull request.
