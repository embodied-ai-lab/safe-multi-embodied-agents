# Safe Multi-Embodied Agents: Answers

Copy this file to `submission/answers.md` and fill in every field. Do not rename
the copy. CSE 494 builds the ZIP with `make submission GROUPID=<your group id>`;
CSE 598 adds `REQUIRE_GRAD=1` so missing start-window results fail packaging.

## Group and run metadata

- Group ID:
- Group members:
- Course: CSE 494 / CSE 598 (delete one)
- Date:
- Setup option (Ubuntu, macOS, or Sol), operating system, Python version, SUMO version:

## Part 1. Baseline

Four agents and their observations:

Physical exclusion rule:

Predictions for delayed grants and slow crossing under `lease`:

| Policy | Completed | Exclusion violation (s) | Collision pairs |
| --- | ---: | ---: | ---: |
| independent | | | |
| lease | | | |

Why SUMO's automatic safety checks are disabled:

## Part 2. Implementation

How the three functions satisfy their contracts:

Why time expiry alone does not establish physical clearance:

Handling a grant received exactly at its deadline, and a retired token:

## Part 3. Controlled comparison

| Scenario | Policy | Completed | Violation (s) | Collision pairs | Max wait (s) | All-clear time (s) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |

Slow-car comparison and causal explanation:

Delayed-grant comparison and causal explanation:

Lossy-message comparison and retransmission behavior:

Figure path and interpretation:

## Part 4. Trace and limitation

Selected scenario:

Baseline event timestamps and their physical consequences:

Corrected event timestamps and their physical consequences:

Collision versus exclusion violation:

Expected behavior under permanent loss of releases:

One assumption and a limitation:

## CSE 598 extension, if applicable

Prediction and fixed experimental settings:

| Start window (s) | Completed | Expired grants | Violation (s) | Max wait (s) | All-clear time (s) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.5 | | | | | |
| 1 | | | | | |
| 2 | | | | | |
| 4 | | | | | |

Interpretation of safety and progress, including step granularity:
