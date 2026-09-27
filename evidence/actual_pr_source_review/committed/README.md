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
