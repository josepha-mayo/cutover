# Browser scenario to three-case PR gate

A synthetic two-record scenario was built in the Cutover browser and its
downloaded CI kit added one entry to `ci/cases.json` in [controlled PR #7]
(https://github.com/josepha-mayo/cutover/pull/7). No workflow YAML changed.
The first [run](https://github.com/josepha-mayo/cutover/actions/runs/36192520938)
created three passing review jobs, but a general test still assumed exactly
two cases and failed. That test was fixed without altering the candidates.
The [final run](https://github.com/josepha-mayo/cutover/actions/runs/36192747474)
passed discovery and all three review jobs; Ubuntu and Windows tests passed.
The control PR was closed unmerged after verification.

| Case | Executed result |
| --- | --- |
| Warehouse / Bob-saved | 116/116 verified pass |
| Parcel / Bob-saved | 116/116 verified pass |
| Browser-built synthetic release / Codex starter | 124/124 verified pass |

Each folder is an exact downloaded GitHub artifact payload: report JSON,
Markdown review, ZIP review packet, job summary and machine verdict. The
custom folder also holds the browser-generated contract and candidate.
All three reports were independently replayed against the final PR head;
all three review ZIPs passed `python -m cutover.audit_bundle --bundle`.
Recheck each raw file against `manifest.json` SHA-256 hashes. These are
synthetic bounded SQLite controls, not production deployment approval or
additional IBM Bob authored code. Bob wrote the original repair plans and
per-case review helper; Codex built the scenario starter and matrix wiring.
