# Safe Multi-Embodied Agents: Coordinating Connected Vehicles at an Intersection

CSE 494/598 · 4 points (common) + 1 point (CSE 598 extension) ·
estimated 4-6 hours after setup

Record every answer in `submission/answers.md` (copy
[`submission/answers_template.md`](submission/answers_template.md)). Keep answers short and cite the result file and field behind each claim: simulated times from `events.jsonl`, numbers from `summary.json` or `comparison.csv`, not impressions from the replay.

Work in your assigned group with one private repository and one group ZIP. The objective is to coordinate three autonomous vehicle agents that share one intersection through a roadside coordinator, when messages can be delayed, lost, or duplicated and a car can move slower than planned. The decision components are simulated and run on a CPU. The CSE 598 extension adds an estimated 1-2 hours.

## Learning objectives

- Describe the information each agent can observe and why the coordinator cannot see the road.
- Explain why a timer alone cannot establish that a physical space is clear.
- Implement identity, request, epoch, and time-window checks for a reservation protocol.
- Measure safety and progress separately: exclusion violations, collisions, waiting time, and completion.
- Trace a failure from a message event through an entry decision to observed vehicle motion.

## Part 0. Setup (required, ungraded)

Follow `README.md` for one of the three setup options, run `python check_environment.py`, and run the supplied baseline:

```bash
python run_lab.py --scenario nominal --mode independent --out results/baseline
```

Open `results/baseline/replay.html`. Read `PROTOCOL.md`. No prior SUMO experience and no GPU is assumed. The supplied simulator settings, controller limits, message transport, and logging are part of the experiment and must stay unchanged for the required comparisons.

## Part 1. Establish the baseline (1 point)

Run the supplied `independent` and `lease` policies for the nominal scenario:

```bash
python run_lab.py --scenario nominal --mode independent --out results/part1-independent
python run_lab.py --scenario nominal --mode lease --out results/part1-lease
```

In `submission/answers.md`, identify the four agents, the information each can observe, and the physical exclusion rule. Predict what a delayed grant and a slower-than-expected car could do to the timer-based `lease` policy. Report the two runs' exclusion-violation seconds, collision pairs, and completed cars. Explain why SUMO's built-in collision avoidance and right-of-way behavior are disabled in this controlled experiment.

## Part 2. Implement the coordination checks (1 point)

Complete only the three marked functions in `cavlab/policies.py`:

1. `choose_request`
2. `grant_is_usable`
3. `release_matches`

Their exact contracts are in `PROTOCOL.md`. Keep the signatures unchanged and do not modify other modules for the required runs. In `submission/answers.md`, explain why timer expiry alone cannot release an occupied physical resource, why a retired token cannot be reused, and what happens to a grant received exactly at its deadline.

Run the `robust` policy for the nominal scenario. A successful launch means the functions no longer raise `NotImplementedError`, not that every corner case is correct. Do not change the scenario or weaken the monitoring to obtain a better result.

## Part 3. Compare the controlled scenarios (1 point)

```bash
python run_matrix.py --out results/comparison
```

The matrix runs four scenarios (`nominal`, `slow_car`, `delayed_grant`, `lossy`) by three policies (`independent`, `lease`, `robust`) at seed 2026 and writes `comparison.csv`. Summarize all 12 runs in `submission/answers.md` with these columns: scenario, policy, completed cars, exclusion-violation seconds, collision-pair count, maximum observed wait, and all-clear time. Write `incomplete` when fewer than three cars cleared.

Compare `lease` with `robust` for the slow car and for the delayed grant. For each, explain one sequence from a message delivery or timer expiry, through an entry decision, to the observed vehicle motion. Include one labeled screenshot of the replay's occupancy timeline or one plot made from `trajectory.csv`, saved under `results/` and referenced from `submission/answers.md`.

For `lossy`, explain the roles of retransmission and duplicate handling. A seed fixes a run for a given implementation, but different policies send different messages, so the same seed does not give an identical packet-loss trace across policies. Keep the configured distribution and seed fixed and make no statistical-significance claims from a single run.

## Part 4. Explain one failure and one limit (1 point)

For either `slow_car` or `delayed_grant`, cite at least three simulated timestamps from `events.jsonl` that explain the timer-based failure, and the corresponding corrected sequence. Distinguish a geometric collision from a violation of the conservative exclusion rule.

Then explain what the corrected coordinator does if every release from a car that already entered is lost forever, and why that is the intended behavior under this lab's assumptions. State one assumption whose failure would invalidate the safety argument, for example truthful clearance messages, correct actuation, a single coordinator that keeps its state, or the shared clock.

## CSE 598 extension. Start window and progress (1 point)

Use the `robust` policy, the `nominal` scenario, seed 2026, no loss, and a fixed 0.8 s one-way message delay. Sweep `lease_seconds` over 0.5, 1, 2, and 4 seconds. In this policy the parameter is the grant's start window, not permission to recycle the intersection after entry.

```bash
python run_lab.py --scenario nominal --mode robust --seed 2026 --delay 0.8 --loss 0 --lease-seconds 0.5 --out results/graduate-window-05
python run_lab.py --scenario nominal --mode robust --seed 2026 --delay 0.8 --loss 0 --lease-seconds 1 --out results/graduate-window-1
python run_lab.py --scenario nominal --mode robust --seed 2026 --delay 0.8 --loss 0 --lease-seconds 2 --out results/graduate-window-2
python run_lab.py --scenario nominal --mode robust --seed 2026 --delay 0.8 --loss 0 --lease-seconds 4 --out results/graduate-window-4
```

`make grad` runs the same four commands. Before running, predict which windows can let a grant arrive in time. Report completion, expired grants, exclusion violations, waiting, and all-clear time for each window. Explain any repeated expired-grant cycle and why a long wait or no completion differs from a collision. Include the 0.1 s delivery-step granularity in your reasoning. Keep the planner, controller limits, initial conditions, and horizon unchanged across the sweep.

## Deliverables

Put your written answers in `submission/answers.md`. Copy `submission/answers_template.md` and fill in every field. Build the ZIP with `make submission GROUPID=<your group id>` (CSE 494) or `make submission GROUPID=<your group id> REQUIRE_GRAD=1` (CSE 598), then upload only that ZIP to Canvas. The CSE 598 form fails if any of the four `results/graduate-window-*` directories is absent. The ZIP must contain your current `cavlab/policies.py` and any other code you changed, `results/part1-*`, `results/comparison/`, and your figure. Do not include environments, model weights, caches, Git metadata, or secrets. Canvas grades the ZIP you upload, not a newer copy on GitHub or Sol, and code that does not run receives limited credit.

## Group work

You may work in a group. One member creates a private repository from the public template, adds the partners as collaborators, and the group clones that private copy on the machine or into the Sol scratch space where it will run. Put the group ID and every member name in `submission/answers.md`. One member uploads the single ZIP. All members receive the same grade.

## Final submission warning

Canvas grades the ZIP you upload, not a newer copy on GitHub or Sol. Inspect the ZIP before you submit, and rebuild and re-upload it if you change anything afterward. Keep `results/` until the ZIP is built; packaging reads it.

## Generative AI

You may use generative AI as an assistant for clarifying concepts, debugging, organizing ideas, or improving writing. You may not rely on it to complete the project without understanding the work. Your group remains responsible for the code, experiments, and explanations, and each member should be able to explain any part of the submission. Work that relies on generative AI without demonstrated understanding may receive reduced credit for the affected parts.
