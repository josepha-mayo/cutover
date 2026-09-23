# Controlled detection ablation — not a customer benchmark

The project needs a measurable claim that survives review. On the **three deliberately unsafe rollout patterns** shipped with Cutover, the new-version baseline detects **0/3**, completed-rollout checks detect **2/3**, and adding migration-statement windows detects **3/3**. This exact result repeats on the Parcel and Relay sample contracts. The two contracts have the same structural rename problem, so this is one curated defect set under two names and seeds, not six independent incidents.

| Stage | Direct rename | One-time backfill | Late bridge | Unsafe patterns detected |
| --- | --- | --- | --- | --- |
| New-version baseline only | Passes 8/8 | Passes 8/8 | Passes 8/8 | 0/3 |
| Completed-rollout schedules | Fails 60/76 | Fails 28/76 | Passes 76/76 | 2/3 |
| Add migration-statement windows | Fails 8/16 windows | Fails 8/24 windows | Fails 16/48 windows | 3/3 |

The late bridge is the incremental finding. It looks safe after the migration finishes, yet a write can arrive after backfill and before synchronization. The 16 failures include old updates and inserts across multiple statement boundaries. The window-safe reference passes 76/76 completed-rollout and 48/48 window probes in each sample. Removing any one of its synchronization triggers causes failures in the existing negative controls.

Reproduce the table with `python -m evidence.build_ablation`; its output is [`evidence/ablation.json`](../evidence/ablation.json). Each candidate runs against fresh SQLite databases with a fixed old adapter and an independent ledger of acknowledged writes. The JSON includes plan, contract, suite and engine hashes. The selected fixtures and input strings define the scope; these numbers are not a general accuracy, incident-reduction, or time-savings estimate.

At the event, record Bob's actual task duration, tool calls, candidate attempts, code changes, and final replay results. If Bob produces a review-ready report, test it on both failing and passing candidates. Do not infer a productivity gain without a measured comparison or a real engineer's feedback.
