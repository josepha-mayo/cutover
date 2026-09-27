# Exact committed SQL control

This download retains a two-commit synthetic Git history, the supplied project
inputs, and the actual comparison/kit from downloaded runtime5659d3b. The candidate
is a prewritten bundled reference, not IBM Bob output or customer adoption.

Inspect receipt.json and the inputs before running. With the current Cutover
checkout as your working directory, use PowerShell:

```powershell
Expand-Archive committed-control.zip -DestinationPath committed-control
git clone committed-control/source.bundle committed-pr
Copy-Item committed-control/inputs committed-pr/my-release -Recurse
Set-Content -LiteralPath committed-pr/db/relocation.sql -Value 'DO NOT EXECUTE THIS CHANGED WORKING FILE;'
python -m cutover.review_project --project committed-pr/my-release --baseline-git-ref 4bf0e9c31aeb2add321c8b4450efa1b494716444 --baseline-git-path db/relocation.sql --candidate-git-ref f973f99fc0b83b7f645e7b534c740d66e7dd535e --candidate-git-path db/relocation.sql --out fresh-committed-review
```

The supplied copied migration.sql remains SELECT1; the changed working source is
also invalid SQL. Neither should be executed. Both committed SQL snapshots produce
original108/124 blocked -> candidate124/124 pass, with their own independently
replayed reports. Only migration SQL comes from the commits; adapters/schema/seeds
are supplied project inputs, not application source extracted from the Git history.
No fetch, branch switch, database connection or source modification is performed
by the reviewer. Passing covers bounded sequential SQLite schedules only.

Inspect the original retained review.html offline, or independently re-audit the
original packet without relabeling it as a new run:

```powershell
python -m cutover.audit_bundle --bundle committed-control/comparison.zip --markdown retained.md --html retained.html
```

Exit1 is expected for verified paired evidence containing a blocked original;
exit2 means unverified. Hashes identify bytes, not authenticity or signatures.

## Try the portable PR handoff

`pr-review.zip` is the actual later handoff from runtime3cb0959 reviewing the same
two synthetic commits. Its exact85,106bytes and SHA256
`05978f8c9954f26ec1880989e6cabbd807506ef0ee105097f5adc9bf666a6e6d`
are retained in `pr-review-receipt.json`. The original108/124 block and
candidate124/124 pass remain distinct; the candidate is a prewritten reference,
not Bob output. This handoff contains SQL snapshots and review outputs, not the
Git repository itself; use committed-control.zip above to reproduce the commits.

Choose Open review packet in the live or local browser and select this ZIP. Or
use the current downloaded local starter without unpacking or uploading it:

```console
python -m cutover.audit_bundle --bundle pr-review.zip --markdown fresh.md --html fresh.html
```

The inner comparison was independently replayed by runtimee379d98 with exit1;
the original blocked report explains that exit. Fresh notes contain only the
replayed comparison evidence. The outer inventory checks byte consistency only;
outer notes, HTML, optional kits and Git labels are not authenticated or
independently verified. The archive is preserved byte-for-byte from its original
export, with its original instructions and metadata unchanged. The CLI and browser
reviewer extensions are Codex work.
