# Controlled detection ablation — not a customer benchmark

The project needs a measurable claim that survives review. On the **three deliberately unsafe rollout patterns** shipped with Cutover, the new-version baseline detects **0/3**, completed-rollout checks detect **2/3**, and adding migration-statement windows detects **3/3**. This exact result repeats on the Parcel and Relay sample contracts. The two contracts have the same structural rename problem, so this is one curated defect set under two names and seeds, not six independent incidents.

| Stage | Direct rename | One-time backfill | Late bridge | Unsafe patterns detected |
| --- | --- | --- | --- | --- |
| New-version baseline only | Passes 8/8 | Passes 8/8 | Passes 8/8 | 0/3 |
| Completed-rollout schedules | Fails 60/76 | Fails 44/76 | Passes 76/76 | 2/3 |
| Add migration-statement windows | Fails 8/16 windows | Fails 8/24 windows | Fails 16/48 windows | 3/3 |

The late bridge is the incremental finding. It looks safe after the migration finishes, yet a write can arrive after backfill and before synchronization. The 16 failures include old updates and inserts across multiple statement boundaries. The window-safe reference passes 76/76 completed-rollout and 48/48 window probes in each sample. Removing any one of its synchronization triggers causes failures in the existing negative controls.

Reproduce the table with `python -m evidence.build_ablation`; its output is [`evidence/ablation.json`](../evidence/ablation.json). Each candidate runs against fresh SQLite databases with a fixed old adapter and an independent ledger of acknowledged writes. Version 0.3.3 requires the new reader to read the target without accessing the old column, new updates and inserts to carry their values into the target on a trigger-free snapshot, and the target column to preserve ledger values. This rejects old-adapter no-ops, a reader that only touches the target in a no-op expression, an updater that self-assigns the target, and a new insert that writes only the old field. Explicit dual-writes remain valid. The JSON includes plan, contract, suite and engine hashes. The selected fixtures and input strings define the scope; these numbers are not a general accuracy, incident-reduction, or time-savings estimate.

The pre-event Codex baseline now supports a third, user-supplied warehouse fixture through the CLI and can write a Markdown review from the executed JSON report. That fixture has the same structural rename problem; it does not increase the independent-incident count or turn this ablation into a general accuracy claim. At the event, record Bob's actual task duration, tool calls, candidate attempts, code changes, and final replay results. The planned Bob extension is an end-to-end browser import/replay workflow, with a PR check example only if time permits. Do not infer a productivity gain without a measured comparison or a real engineer's feedback.
