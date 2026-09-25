# Browser-built red/green CI kit

[`cutover-my-release-ci-kit.zip`](cutover-my-release-ci-kit.zip) is the exact
download produced by the live Render-hosted Cutover browser after submitting the guided
synthetic `items.location` → `items.destination` scenario on September 25,
2026. The user-selected incoming old-worker write was `R-07`; the unsafe
one-time backfill's first failing new read returned `A-01`. The generated
bridge candidate passed its own bounded suite. These browser and kit features
are Codex event work, not IBM Bob-authored code.

The archive contains the contract, passing candidate, blocked baseline,
manifest entry, both executed reports and reviews, and a standalone failing
witness. Its SHA-256 is
`987eca5db34569563a85821146c3ad7558ab258360f99d2dbc6b3135dc0ac1ac`.
The extracted plans were run through `ci/review_gate.py` in this repository:

| Control | Independent gate verdict | Coverage | Plan hash prefix |
| --- | --- | ---: | --- |
| Unsafe one-time backfill | `verified_block` | 44/100 | `427bff109d3f` |
| Generated compatibility bridge | `verified_pass` | 124/124 | `094e61d8f32f` |

`python -I evidence/unsafe-control-witness.py` from the extracted archive
reproduced the mismatch (`expected: R-07`, `actual: A-01`). The passing plan
alone is listed in `manifest-entry.json`; the unsafe control is deliberately
excluded from a normal green PR. This is a synthetic SQLite demonstration,
not a production deployment approval. See the [controlled three-case PR](../ci_browser_control/README.md)
for a separate GitHub-hosted check using a browser-built kit.

The current checkout also offers `python -m ci.install_kit --kit PATH_TO_ZIP`
as a no-write preflight. After reviewing its hashes and target file list,
repeat with `--apply` to add the passing case to `ci/cases.json`. The installer
never adds the unsafe control to the green manifest.
