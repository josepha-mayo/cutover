# Take a failed rehearsal into a local Bob workspace

This is the actual ZIP downloaded through the live Render browser on September 26, 2026, using source commit `6b640ad5de085cddb493231034fe9ddfb18d942c`. It contains the failed Warehouse inputs, their fresh report, the fixed evaluator, local MCP setup, a Bob task and a standalone candidate verifier. It includes no credentials, machine-local MCP configuration, automatic tool approvals or bundled passing reference repairs.

[Download the actual workspace](cutover-warehouse-bob-workspace.zip) and [inspect its verification record](verification.json). SHA-256: `44a34392e06752a771412d0bd154633c6825800d3c66fa8dd130a83ff0c7a0c0` (42,200 bytes).

The actual extracted archive was checked:

| Check | Observed outcome |
| --- | --- |
| Packaged failed plan, independently replayed | Blocked, 108/124 |
| Historical saved Bob Warehouse candidate, supplied separately | Passed, 116/116 |
| Attempt retention | Both reports and Markdown retained in distinct verification folders |
| Local MCP configuration | Correct interpreter/workspace paths; automatic approvals empty |
| SDK stdio contract validation and rehearsal | Valid contract; actual tools reproduced the 108/124 block |

Extract into a new folder and follow the included README. Its inventory verifier checks the fixed files; it does not establish publisher authenticity. Run `python verify_workspace.py --candidate baseline-plan.json` to reproduce the block. To check the already public historical repair, download [that saved candidate](../../bob_sessions/warehouse-07a20bdb56f5-candidate.json) separately and pass its path with `--candidate`. Each attempt writes new evidence under `work/`.

A new repair requires a real local Bob IDE session and its actual task history and summary. This archive does not invoke Bob. The SDK checks do not prove Bob IDE host setup, new Bob authorship, production safety or customer adoption. Bob authored the historical repair; Codex authored this handoff and its verification. [Full attribution and limits](../../docs/PROVENANCE.md).
