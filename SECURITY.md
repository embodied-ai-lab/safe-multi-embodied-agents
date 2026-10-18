# Safety and security model

This project is a CPU simulation of three connected vehicles and one roadside coordinator. Nothing in it controls a real vehicle, and a finite set of simulated runs is not a safety proof. Read this before implementing Part 2 and before writing the limitations in Part 4.

## What is simulated and what is trusted

- SUMO is the physical plant. Its own collision avoidance and lane-change checks are switched off for the three cars so that a bad coordination policy is not rescued by the simulator; the lab's speed controller bounds acceleration and braking instead.
- The simulated network is the only fault model: configured delay, loss, and duplication, reproducible from a seed. A message sent in one step is delivered no earlier than the next step.
- Ego sensing is idealized: each car reads its own road, lane position, and speed exactly. The coordinator sees delivered protocol messages only. The evaluation monitor reads every car's position for metrics and never feeds anything back to an agent or planner.
- Message identities are trusted labels. Checking `sender == "RSU"` is a label check, not source authentication.

## What the corrected protocol establishes

Within the tested scenarios, a car commits to enter the conflict zone only while stopped at its gate with a grant that is addressed to it, belongs to its current trip, carries an epoch newer than any it has retired, and is used before its start deadline. The coordinator holds one reservation at a time and frees it only on a matching release that reports `cleared` or `expired`, never because time passed. In the four graded scenarios at seed 2026 this produced zero exclusion violations and zero collisions. That is an observation about this simulation and its 0.1 s sampling, not a guarantee for continuous trajectories, other seeds, or real roads.

## What it does not establish

- No authentication, integrity, or confidentiality of messages. A forged grant, a false `cleared` release, or a replayed message from a malicious party is outside the experiment.
- No protection against a faulty or malicious vehicle, a coordinator restart, or behavior that ignores the protocol.
- No progress guarantee under permanent message loss. The `permanent_release_loss` scenario shows the coordinator correctly refusing to admit the next car while the released car's report never arrives.
- The exclusion rule is conservative: an exclusion violation is not a collision, and a collision-free trace is not evidence of safety.
- Waiting time is a cost of the corrected policy and must be reported together with completion.

## Data and secrets

The lab uses no credentials, keys, tokens, or model weights. Result directories contain only simulation records: `summary.json`, `trajectory.csv`, `events.jsonl`, `metadata.json`, `sumo.log`, and `replay.html`. The replay page makes no network requests. Internet access is needed only to install the pinned packages or obtain the container image; the experiments contact no external service. Do not place secrets, personal data, or large binaries in the lab directories; the submission packager excludes environments, Git metadata, hidden files, container images, and archives, but it includes everything else under `results/` with a recognized file type.

## Responsible use

Run the simulation only in your own environment or your own Sol allocation, never on a Sol login node. Do not interfere with other users' processes or storage. Report a reproducible crash, a result that contradicts the recorded settings, or an unexpected file in your submission ZIP to the instructor.
