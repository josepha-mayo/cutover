# Installed browser kit: exact PR evidence

The browser-generated synthetic release kit was applied with the guarded
`python -m ci.install_kit --kit … --apply` command in [controlled PR #8]
(https://github.com/josepha-mayo/cutover/pull/8). The PR changed exactly three
inputs: one contract, one passing candidate, and one `ci/cases.json` entry.
It did not edit the GitHub Actions workflow. The unsafe control remained in
the downloadable kit; it was independently replayed as a verified block,
not registered as a green candidate.

The first [general check run](https://github.com/josepha-mayo/cutover/actions/runs/36196643824)
failed because the installer test fixture assumed the custom slug was not yet
in the manifest. The test was corrected on main in commit `08cc84c`; the
candidate files were unchanged. At corrected PR head
`472728f3a47c434f131fbf226a0c0d931cb83a1e`, the
[review run](https://github.com/josepha-mayo/cutover/actions/runs/36196962880)
created three independent green jobs, and the
[general checks](https://github.com/josepha-mayo/cutover/actions/runs/36196962914)
passed on Ubuntu and Windows. The synthetic PR was closed without merging.

| Case | Exact downloaded result | Evidence |
| --- | --- | --- |
| Warehouse, Bob-saved repair | 116/116 verified pass | [Report](cutover-warehouse-review-evidence/report.json) · [Verdict](cutover-warehouse-review-evidence/verdict.json) · [Review ZIP](cutover-warehouse-review-evidence/review.zip) |
| Parcel, Bob-saved repair | 116/116 verified pass | [Report](cutover-parcel-review-evidence/report.json) · [Verdict](cutover-parcel-review-evidence/verdict.json) · [Review ZIP](cutover-parcel-review-evidence/review.zip) |
| Browser-built synthetic release, Codex starter | 124/124 verified pass | [Report](cutover-release-my-release-review-evidence/report.json) · [Verdict](cutover-release-my-release-review-evidence/verdict.json) · [Review ZIP](cutover-release-my-release-review-evidence/review.zip) |

Each folder also contains the exact downloaded `review.md` and `summary.md`.
All three reports were independently replayed against the contract and plan
at that PR head. Every review ZIP passed the bundle audit; verdicts and job
summaries agreed with their reports. [The manifest](manifest.json) records
SHA-256 hashes of every mirrored payload. These hashes make alterations to
this mirror detectable; they are not a signature or a production-safety claim.

The installer, browser starter, and manifest wiring are Codex work after the
event-period Bob IDE tasks. Bob authored the saved Parcel/Warehouse repair
plans and the original per-case review gate, documented in
[provenance](../../docs/PROVENANCE.md).
