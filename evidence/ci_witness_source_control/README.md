# Source-linked lost-write evidence

In [control PR #14](https://github.com/josepha-mayo/cutover/pull/14), the
[verified run](https://github.com/josepha-mayo/cutover/actions/runs/36218262819)
checked three prospectively specified cases using Action
`3fe6630c41d6220defc1107d9ead18d905720b1a`.
The control PR was closed unmerged after the artifacts and rendered annotation
were verified. Its source commits, initial run and final run remain public.

| Case | Independently replayed result | GitHub annotation |
| --- | --- | --- |
| [Late bridge](late-window/summary.md) | Blocked 108/124 | Migration SQL line 8, after statement 2 |
| [Completed-rollout defect](completed-rollout/summary.md) | Blocked 100/132 | File only; no inferred window line |
| [Saved Bob Warehouse repair](bob-repair/summary.md) | Passed 116/116 | No failure annotation |

The [line-8 PR annotation](https://github.com/josepha-mayo/cutover/pull/14/files#annotation_81115515500)
and [downloaded GitHub annotation record](late-window/github-annotations.json)
show the same witness: old.write arrived after SQL 2, row 11 expected `R-07`,
but the new reader observed `A-01`. Line 8 ends the one-time backfill;
synchronization starts afterward. The location identifies the observed boundary,
not a claim that one line alone caused the defect.

The gate derives that location only when the independently verified witness
contains the matching successful migration prefix and old-worker operation.
Multistatement triggers remain one SQLite statement. Local and CI tests include
multiline comments, BOM/CRLF source files, and rejection of mismatched traces.
Inline messages use escaped newlines so all four lines remain visible beside
the SQL. The [initial successful run](https://github.com/josepha-mayo/cutover/actions/runs/36217924671)
used a single-line message; the later run verifies its readability refinement.

All three downloaded ZIPs passed independent replay. Their effective plans,
contracts, source hashes and annotations were bound to actual merge checkout
`68bddf1c9de9cf4800ac4d3422a6a554b769bfbd` and PR head
`c11871be4fe0f555c82408868f6ad9c5e3494cc5`.
[manifest.json](manifest.json) hashes the 24 exact downloaded artifact/annotation
files and nine checked-out inputs below `source_inputs/`. Git line-ending
conversion is disabled for this mirror. These hashes support comparison;
they are not a signature or proof of origin by themselves.

To replay one packet from the repository root:

```powershell
python -m cutover.audit_bundle --bundle evidence/ci_witness_source_control/late-window/review.zip
```

That command exits 1 for a verified block, and 0 for the passing Bob packet.
Expected failing Actions used continue-on-error only so the next assertion
could verify the actual failed step and classification. Overall green controls
mean their predefined outcomes matched, not that both unsafe migrations passed.

This source presentation, Action packaging and synthetic control are Codex
extensions to Bob's original gate. The passing SQL is Bob's previously retained
event candidate; this run is not a new Bob task. No production incident or
deployment-safety claim is made. Original Bob task evidence remains in
[`bob_sessions`](../../bob_sessions).
