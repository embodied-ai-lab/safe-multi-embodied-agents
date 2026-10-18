# Safe Multi-Embodied Agents: Coordinating Connected Vehicles at an Intersection

> This template repository is designed as a project lab for the combined course of
> [CSE 494](https://catalog.apps.asu.edu/catalog/classes/classlist?keywords=85268&searchType=all&term=2267)
> and [CSE 598](https://catalog.apps.asu.edu/catalog/classes/classlist?keywords=87933&searchType=all&term=2267),
> "Topic: Intelligent and Safe Cyber-Physical Systems" (ISCPS in short),
> at Arizona State University (ASU) in Fall 2026.
> If you have any questions about this project lab, please get in touch with the instructor,
> [Hokeun Kim](https://hokeun.github.io/), via [hokeun@asu.edu](mailto:hokeun@asu.edu).

This project puts three simulated connected vehicles and one roadside coordinator at a single intersection. The cars approach from different directions and the coordinator grants permission to cross. [SUMO](https://sumo.dlr.de/) simulates the vehicle motion on a CPU, Python implements the agents and the simulated message network, and a browser page replays each recorded run. You implement and evaluate the coordination rules that decide when the next car may enter when the previous car has not yet confirmed that it is clear.

## Start here

Read [ASSIGNMENT.md](ASSIGNMENT.md) for the graded parts, and [PROTOCOL.md](PROTOCOL.md) for the coordination protocol and the three functions you complete in `cavlab/policies.py`. [SECURITY.md](SECURITY.md) states what the coordination does and does not guarantee; read it before Part 2 and Part 4. This file covers setup and the command surface.

## Create your private repository

1. Open this GitHub template repository and select **Use this template**, then **Create a new repository**.
2. Create it under one group member's account with a clear name, for example `group05-safe-multi-embodied-agents`, and set the visibility to **Private**.
3. Add only your project partners as collaborators.
4. Clone your private repository onto the machine where you will run the lab, or into `/scratch/$USER` on Sol. Do not work in this template.

## Choose one setup option

| Option | Instructions | Where experiments run |
| --- | --- | --- |
| Native Linux, primarily Ubuntu 24.04 | [setup/UBUNTU.md](setup/UBUNTU.md) | A Python virtual environment on your computer |
| Native macOS | [setup/MACOS.md](setup/MACOS.md) | A Python virtual environment on your Mac |
| ASU Sol with Apptainer | [setup/SOL.md](setup/SOL.md) | A CPU allocation using an Ubuntu-based container image |

All three use SUMO 1.28.0, Python 3.12, and the same assignment. No GPU, model download, Docker, ROS 2, or display server is required. Internet access is needed once to install packages or obtain the container image; the experiments themselves contact no external service. A Linux virtual machine or WSL following the Ubuntu instructions is a secondary alternative that we do not recommend as a first choice, and troubleshooting support focuses on the three main options.

## Check the environment

```bash
python check_environment.py
```

This reports Python, the pinned SUMO packages, the `sumo` and `netconvert` executables and their versions, the lab files, and one headless TraCI launch. It is an infrastructure check only: passing means the tools are ready, not that your implementation or any experiment is correct. On Sol, prefix every `python` command with `bash scripts/sol_exec.sh` after following the Sol setup.

## Run and inspect

```bash
python run_lab.py --scenario slow_car --mode lease --out results/slow-lease
python run_lab.py --scenario slow_car --mode robust --out results/slow-robust
```

The two supplied baselines, `independent` and `lease`, run immediately. The `robust` policy exits with an explicit "implementation required" message until the three functions are completed. Use a new `--out` directory for every run; existing results are never overwritten. Warnings printed by SUMO, including collision warnings in the unsafe baselines, go to stderr; the run summary is printed as JSON on stdout.

Each result directory contains:

| File | Purpose |
| --- | --- |
| `replay.html` | Open directly in a browser. Play or scrub the recorded motion, the per-car state, the coordination events, and the occupancy timeline |
| `summary.json` | Completion, waiting, overlap, collision-pair, message, and timing metrics |
| `trajectory.csv` | Position, speed, applied speed command, road, phase, occupancy, and token for every car at every 0.1 s step |
| `events.jsonl` | Message send, drop, and delivery events, grants, entry commitments, clearances, and monitor events |
| `metadata.json` | Effective configuration, seed, controller limits, SUMO options, package versions, platform, and lane geometry |
| `sumo.log` | Simulator warnings. Collisions are expected in some unsafe baselines |

Open `replay.html` with a file manager or browser. It needs no web server and makes no external requests. On Sol, download the file and open it on your own computer. All times shown are simulated seconds; `wall_seconds` in `summary.json` is the local execution time and is not comparable between machines. Optional: add `--gui` to a run if `sumo-gui` and a desktop are available. The graded workflow does not depend on it.

## Command guide

`make help` lists the targets. Every target is a thin wrapper over the Python command shown next to it, so either form is fine.

| Command | Python equivalent | Purpose |
| --- | --- | --- |
| `make check` | `python check_environment.py` | Infrastructure check, not a correctness check |
| `make baseline` | `python run_lab.py --scenario nominal --mode independent --out results/baseline` | Part 1 baseline |
| `make run SCENARIO=slow_car MODE=lease` | `python run_lab.py --scenario slow_car --mode lease --out results/slow_car-lease` | One run |
| `make matrix` | `python run_matrix.py --out results/comparison` | Part 3: the 12 required runs and `comparison.csv` |
| `make grad` | four `run_lab.py` calls with `--delay 0.8 --loss 0 --lease-seconds ...` | CSE 598 start-window sweep |
| `make replay-planner` | `python run_lab.py --mode robust --planner replay --planner-file scenarios/replay_example.json --out results/replay-planner` | Replace the planner with the synthetic replay component |
| `make submission GROUPID=05` | `python package_submission.py --groupid 05` | One group ZIP under `submission/` |

On Sol, run the same targets inside the container with `make PY="bash scripts/sol_exec.sh python" <target>`.

## Required comparison

After implementing the three functions:

```bash
python run_matrix.py --out results/comparison
```

This runs four scenarios by three policies at seed 2026 and writes `comparison.csv` plus one result directory per run. Message delay advances simulated time while the cars keep moving; nothing sleeps. A fixed seed makes a run reproducible for a given implementation, but different policies send different messages, so the same seed does not produce the same packet-loss trace across policies.

## Replace a decision component

The default planner is a rule that proposes 6 m/s. Two alternatives show that the planner is replaceable without touching the coordination protocol:

```bash
python run_lab.py --mode robust --planner replay --planner-file scenarios/replay_example.json --out results/replay-planner
python run_lab.py --mode robust --planner cavlab.example_planner:make_planner --out results/custom-planner
```

A custom module exposes a zero-argument factory that returns an object with `propose(observation)` returning `cavlab.planners.Proposal(target_speed=...)`. Each vehicle gets its own instance, the observation contains only that car's own state, and the gate, grant checks, and speed limits stay outside the planner. Real model loading and GPU execution are not part of this lab. The planner call is synchronous, so a slow model would pause simulated time rather than model inference latency; `planner_wall_seconds` in the summary reports the time spent inside planner calls.

## Submission

Record every answer in `submission/answers.md`. Create it once from the template, fill it in, then package the current working tree, including changes you have not committed:

```bash
test -e submission/answers.md || cp submission/answers_template.md submission/answers.md
# fill in submission/answers.md; the command above never overwrites it
make submission GROUPID=<your group id>                  # CSE 494
make submission GROUPID=<your group id> REQUIRE_GRAD=1   # CSE 598: fail unless the four start-window results exist
unzip -l submission/group<your group id>_safe-multi-embodied-agents.zip
```

The ZIP contains `answers.md` at its root, the lab code, configuration, the setup notes, and everything under `results/` with a recognized file type. It excludes virtual environments, caches, Git metadata, hidden files, container images, and archives. Put custom Python modules under `cavlab/`, configuration under `scenarios/`, and figures under `results/` so they are included. Do not put keys, passwords, or model weights in the lab directories. One group member uploads the single ZIP to Canvas. Canvas grades the uploaded ZIP, not a newer copy on GitHub or Sol, so inspect it before submitting. CSE 598 work goes in that same ZIP; Canvas has a separate grade item for the extra point with no second upload.

## License

BSD 2-Clause, see [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). SUMO is a separately licensed dependency installed from PyPI or built into the container image; it is not redistributed in this repository.
