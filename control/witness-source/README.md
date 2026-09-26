# Prospective source-annotation control

These synthetic PR jobs test a Codex extension to Bob's original review gate.
The expected outcomes were checked in before the jobs ran. Failing Action steps
use continue-on-error only so the next step can assert their actual failure and
classification. The late-window annotation should point to line 8, after SQL 2;
this is an observed interleaving boundary, not a claim of single-line causality.
The completed-rollout failure must not invent a window location. The passing
case replays Bob's previously saved Warehouse repair; this is not a new Bob task.
