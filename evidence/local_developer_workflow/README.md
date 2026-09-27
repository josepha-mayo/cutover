# Reproduce a developer's local release review

Extract developer-workflow-proof.zip into a new folder. Inspect its source. Python 3.10+ is sufficient; no pip install, account or SQL upload is needed for these review commands.

## 1. Catch the unsafe backfill and prepare a repair task

```text
python -m cutover.review_project --project demo-inputs --out fresh-block --bob-workspace
```

Expected exit 1: candidate BLOCKED 55/125. Inspect fresh-block/review.md for the acknowledged GATE-09 write and reader mismatch. fresh-block/bob-repair-workspace.zip contains the failed contract/plan, fixed evaluator, TASK.md and optional local MCP setup. Extract it separately and follow its README if you want to use Bob IDE. Preparing it does not invoke Bob or establish IDE acceptance.

## 2. Review a separately supplied repair and get a PR kit

```text
python -m cutover.review_project --project demo-inputs --candidate-plan supplied-reference.json --out fresh-pass
```

Expected exit 0: candidate PASS 155/155. The independently audited comparison preserves the original 55/125 block. The supplied plan's migration is used even though demo-inputs/migration.sql is still unsafe. Inspect fresh-pass/review.md, including changed SQL lines, and pr-kit.zip. The kit binds the reviewed contract and candidate; inspect its four consumer files before adding it to a repository.

This supplied repair is a prewritten Warehouse reference adapted to the synthetic shipments/loading_bay/dispatch_bay names. It is NOT Bob output or customer adoption. Both steps are Codex workflow enhancements; the two actual event-period Bob IDE tasks remain separately documented in bob_sessions.

## Retained evidence and limits

retained/ contains the actual earlier HTTP-download local acceptance outputs: blocked handoff at source 68ce5c4 and saved-plan repair at source 52054bc. This pack's runtime is the actual live starter downloaded at 52054bc2d0e8d472299fbe288a0f839a0b2e5784; no new IDE run is claimed. Fresh timestamps and ZIP bytes will differ. MANIFEST.json records packaged hashes, not publisher authenticity.

Different SQL sequences have separately tested statement boundaries: 55/125 versus 155/155 is not an equivalent-denominator productivity claim. This is bounded sequential SQLite evidence; no simultaneous transactions, other database engines or production safety are established. Synthetic apostrophe, Unicode and empty-string inputs are retained. The commands run local disposable SQLite; exported artifacts include SQL and values. Existing output folders are refused; choose new names for another attempt. Ordinary review is standard-library-only; optional Bob integration requires the pinned MCP SDK and your separate Bob IDE access.
