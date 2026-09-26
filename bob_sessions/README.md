# IBM Bob IDE event evidence

Two substantive IBM Bob IDE tasks were run during the September 25-27, 2026 event on the hackathon-provisioned account. Their required consumption-summary PNGs, IDE-exported histories and saved outputs are linked below. Codex independently checked the candidates and CI outcomes; those checks are not additional Bob tasks.

| Event task | Required IDE summary | Exported history | Saved work and verification |
| --- | --- | --- | --- |
| 01 - Parcel and Warehouse repair, `07a20bdb56f595035652c2e6732b2c53` | [Task 01 PNG](cutover_task01_parcel_warehouse_repair_07a20bdb_summary.png) | [Task 01 history](cutover_task01_parcel_warehouse_repair_07a20bdb_history.md) | [Parcel candidate](parcel-07a20bdb56f5-candidate.json), [116/116 report](parcel-07a20bdb56f5-report.json); [Warehouse candidate](warehouse-07a20bdb56f5-candidate.json), [116/116 report](warehouse-07a20bdb56f5-report.json), [provenance and hashes](warehouse-07a20bdb56f5-evidence.json) |
| 02 - Original PR review gate, `9aa1e2a2ae601940eb12f45bd6c2bf59` | [Task 02 PNG](cutover_task02_ci_review_gate_9aa1e2a2_summary.png) | [Task 02 history](cutover_task02_ci_review_gate_9aa1e2a2_history.md) | [Task record](cutover_task02_ci_review_gate_9aa1e2a2_evidence.json); [independently checked unsafe, passing and regressed GitHub controls](../evidence/ci_controls/README.md) |

The repair history preserves the earlier recursive-trigger failure before the saved passing candidates. The history exports retain their observed status text; the saved candidates and independent reports establish the measured outcomes separately. A PNG or task-history label alone does not establish correctness.

Each repair passed 116/116 probes on its fixed synthetic SQLite contract. This is bounded evidence, not production safety, concurrent transaction coverage or customer adoption. The original gate distinguishes verified blocks from unverified execution errors and retains review artifacts on failure.

Codex built the evaluator and browser before kickoff. Later features, including the reusable Action, scenario and kit exports, contract lock, packet viewer, source annotations, selected replay and comparison presentation, are Codex extensions. They must not be attributed to these Bob tasks. See [complete provenance and limits](../docs/PROVENANCE.md).

The [official September guide](https://lablab-ibm-bob-2-hackathon-guide.s3.us.cloud-object-storage.appdomain.cloud/index.html) requires Bob IDE as a core component and a clearly named PNG of every relevant task-session summary in this folder. Pre-event Shell readiness checks are private preparation and are not qualifying event contributions. No additional Bob task is claimed here.
