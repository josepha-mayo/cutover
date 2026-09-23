# Product decision — 2026-09-23

Cutover is a provisional product hypothesis, not a claim that a win is assured.

## The decision after competitive review

| Candidate | Strongest argument | Reason not to lead with it |
| --- | --- | --- |
| Repository onboarding map | Clear, visual, easy to demonstrate | Atlas already placed second in the first Bob event with this exact workflow. |
| AI code provenance | Concrete enterprise artifact and strong Bob integration | Pedigree already won the first Bob event with commit attestations and a custom Bob mode. |
| Generic incident reproduction and repair | Large developer pain; easy to understand | Without authentic incidents and a reliable reproducer, tomorrow's demo risks being a staged bug fixer. |
| Legacy app modernization | Excellent IBM alignment | Bob already ships specialized modernization workflows. A credible differentiated migration needs a substantial real legacy target and compatibility evidence. |
| Broad deployment risk simulator | High presentation potential | Sandbox already placed third in the first Bob event. A broad risk score would require validation we do not have. |
| Mixed-version release rehearsal | A small, executable correctness problem with a visible business consequence | Select, but only with actual executions, fixed independent contracts, editable candidates, negative controls and explicit scope. |

## The important correction to the initial idea

Detecting a renamed database column is not original. Atlas already documents backward-compatibility linting and executable migration tests. Expand/contract is an established technique, not our invention.

The useful product question is narrower: after the migration succeeds, do every old and new reader observe each acknowledged update and inserted record, including after the application rolls back? And can an old worker write between migration statements without leaving the new column stale? A one-time backfill or late synchronization can satisfy completed-rollout checks while violating those properties.

Cutover generates a bounded matrix of old/new write/read schedules and old-write injection at each migration statement boundary. It executes them and produces a replay with SQL, inputs, expected values and actual values. Bob receives that counterexample through MCP and proposes a repair. The evaluator remains independent of the candidate. This makes the repair assessable rather than relying on an AI assurance or risk score.

## What would falsify this direction

- The tool only catches errors already visible in the new-version baseline.
- The reference repair only works for the first example's names or values.
- Removing one synchronization direction still receives a passing result.
- A judge cannot change SQL and see a different, reproducible outcome.
- Bob does not contribute a real inspected repair or extension, with session evidence.

## Target buyer and first use

Hypothesis: a backend engineer reviewing a schema-changing release for a service with long-lived workers. The immediate output is a reproducible blocking case or a bounded passing report attached to review. No savings, customer demand, or incident-reduction percentages are claimed without measurement.

Tomorrow's internal target: verified local tool, live editable demo, MCP contract check, and a ready Bob task. Official Bob access is advertised for September 25; the September 27 deadline remains the submission deadline. Pre-event preparation must be disclosed; the published event page encourages a head start but does not establish unrestricted pre-existing-code eligibility. Recheck kickoff instructions before submission.

## Primary sources reviewed

- [Event requirements and schedule](https://lablab.ai/ai-hackathons/ibm-bob-2-hackathon)
- [First event winners](https://lablab.ai/ai-hackathons/ibm-bob-hackathon/live)
- [Pedigree](https://lablab.ai/ai-hackathons/ibm-bob-hackathon/ctrlcats/pedigree)
- [Atlas, the hackathon entry](https://lablab.ai/ai-hackathons/ibm-bob-hackathon/atlas/atlas)
- [Sandbox](https://lablab.ai/ai-hackathons/ibm-bob-hackathon/404/sandbox-castles-crumble-fix-them-first)
- [Atlas migration analyzers](https://atlasgo.io/lint/analyzers)
- [Atlas migration tests](https://atlasgo.io/testing/migrate)
- [Bob modernization capabilities](https://bob.ibm.com/blog/pp_for_java_announcement/)

Descriptions above summarize competitors' own published descriptions; their implementation claims have not been independently audited. The strategic comparison is our judgment.
