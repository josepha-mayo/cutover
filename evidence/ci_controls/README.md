# Cutover event PR controls

These are synthetic release examples from three independently audited pull-request runs. Red is the expected result for unsafe and regressed plans. GitHub may ask signed-out viewers to log in for job logs; the executed reports, summaries, verdicts, and review bundles are mirrored here with SHA-256 file digests. The passing result covers this SQLite contract and tested schedules, not a production deployment.

| Control | Outcome | GitHub | Public evidence |
|---|---|---|---|
| Unsafe | blocked 108/124 | [PR run](https://github.com/josepha-mayo/cutover/actions/runs/36165105646) | [Summary](unsafe/summary.md) · [Report](unsafe/report.json) · [Review](unsafe/review.md) · [ZIP](unsafe/review.zip) |
| Safe Reference | pass 124/124 | [PR run](https://github.com/josepha-mayo/cutover/actions/runs/36165215088) | [Summary](safe_reference/summary.md) · [Report](safe_reference/report.json) · [Review](safe_reference/review.md) · [ZIP](safe_reference/review.zip) |
| Regressed | blocked 100/116 | [PR run](https://github.com/josepha-mayo/cutover/actions/runs/36165290677) | [Summary](regressed/summary.md) · [Report](regressed/report.json) · [Review](regressed/review.md) · [ZIP](regressed/review.zip) |
