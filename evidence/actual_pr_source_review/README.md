# Actual PR SQL source review

This is a synthetic repository control, not customer adoption, production approval or new IBM Bob output. It used the actual hosted local starter at main 3ff071f. Both SQL files include their original UTF-8 BOM and CRLF bytes.

The original unsafe Warehouse SQL was prospectively committed at the local Git commit in receipt.json. Its working-tree db/relocation.sql was then replaced with a prewritten bundled reference repair. The copied project migration.sql deliberately contained SELECT 1, so it could not stand in for the actual PR source.

The executed command used all three source arguments together:

```text
python -m cutover.review_project --project my-release --baseline-git-ref origin/main --baseline-git-path db/relocation.sql --candidate-migration-file db/relocation.sql --out review-pr
```

Original Git SQL blocked 108/124. Actual candidate file passed 124/124. The reviewer retained the exact Git commit/path/blob, both byte-exact SQL snapshots and the unchanged copied project inputs. The command did not fetch, switch branches, edit source files or change the Git working tree. The passing PR kit and its unsafe control matched all four identities of the independently audited comparison.

## Inspect or replay

comparison.zip retains both reports and their complete inputs. pr-kit.zip is the actual exported kit; inspect its README before using its four files. receipt.json records hashes and bounded results, not publisher authenticity. Adapters and contract were supplied inputs; this is not a full application diff or simultaneous transaction coverage.

Using the current local starter, independently audit this retained packet:

```text
python -m cutover.audit_bundle --bundle path/to/comparison.zip --markdown retained-review.md --html retained-review.html
```

Exit 1 is expected for a verified paired packet containing the original blocked baseline; exit 2 means unverified. Do not relabel the original reports as newer runs.

To run a new review from these exact source inputs (without reconstructing the original Git repository), use explicit SQL files:

```text
python -m cutover.review_project --project path/to/inputs --baseline-migration-file path/to/inputs/supplied-baseline.sql --candidate-migration-file path/to/inputs/supplied-candidate.sql --out fresh-review
```

This freshly executes both plans and should return candidate pass, while preserving the original blocked baseline. It uses source files, not the original recorded Git provenance. The prewritten passing reference is test input, not a Bob-generated repair. Passing remains bounded sequential SQLite evidence.

## Compare two exact committed SQL versions

The later [committed-source control](committed/README.md) includes a [downloadable Git history and review ZIP](https://raw.githubusercontent.com/josepha-mayo/cutover/main/evidence/actual_pr_source_review/committed/committed-control.zip). Both SQL sources were prospectively committed before execution. The working file was then changed to invalid SQL, while the copied project migration remained stale. Cutover reviewed the committed blobs: original **108/124 blocked → candidate 124/124 pass**.

The download contains the two-commit Git bundle, actual recorded review and PR kit, supplied inputs, hashes and a PowerShell recipe. Independently cloning that bundle restored both byte-exact SQL blobs; the documented fresh-review recipe reproduced the result without changing the working SQL. The candidate is a prewritten reference, not new Bob output. Candidate commit/path/blob and exact SQL byte hash appear in the note and offline review. The runtime was 5659d3b; this later control does not replace the earlier working-file control above.
