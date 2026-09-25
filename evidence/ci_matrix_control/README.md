# Two-contract pull-request control

[Closed draft PR #4](https://github.com/josepha-mayo/cutover/pull/4) changed only
`ci/parcel-candidate.json` from Bob's saved passing Parcel repair to the
prewritten, unsafe Parcel late bridge. The Warehouse candidate stayed as
Bob's saved passing repair. This was a synthetic control and must not be
merged.

The [GitHub workflow run](https://github.com/josepha-mayo/cutover/actions/runs/36183958224)
evaluated both contract/plan pairs at PR head
`e12447c01659c5e444499271f7f03069df38ef43`:

| Case | Check | Fresh report | Independent replay |
| --- | --- | --- | --- |
| Parcel | Verified block, 108/124 | [Report](parcel/report.json) · [Summary](parcel/summary.md) · [Verdict](parcel/verdict.json) | Block confirmed, audit exit 1 |
| Warehouse | Verified pass, 116/116 | [Report](warehouse/report.json) · [Summary](warehouse/summary.md) · [Verdict](warehouse/verdict.json) | Pass confirmed, audit exit 0 |

Both GitHub jobs uploaded their JSON report, Markdown review, ZIP packet,
summary, and verdict despite the overall run being red. Exact downloaded
files are mirrored in the two folders for signed-out review. Their SHA-256
digests, report hashes, source commit, and audit exits are in
[manifest.json](manifest.json). The Parcel witness is an old write after
backfill: row 101 should read `18 Marina Road` but the new reader sees
`4 Broad Street`.

Bob IDE authored the underlying review gate and both safe repairs. Codex
added the two-case workflow matrix, created the synthetic PR control, and
independently replayed its downloaded evidence. This proves isolation for
these two checked-in SQLite contracts and this PR; it does not certify
untested migrations or production databases.
