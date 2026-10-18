# Option 1: Native Linux, primarily Ubuntu

Ubuntu 24.04 LTS with Python 3.12 is the reference installation and the one the instructor validated. Other Linux distributions work with equivalent packages. All graded runs are CPU-only and headless.

## Install system packages

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip ca-certificates \
    libatomic1 libgomp1 libgl1 libglu1-mesa libx11-6 libxext6 libxrender1 libsm6 libice6 libfontconfig1
```

The shared libraries are what the `eclipse-sumo` wheel from PyPI needs at run time. The `sumo` executable arrives with that wheel, so no SUMO system package or `SUMO_HOME` setting is required. Do not run these `sudo` commands on Sol; the Sol option installs the same packages inside a container image.

## Create the environment and check it

From the lab directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python check_environment.py
```

The check should report SUMO 1.28.0 for the packages and the executables, and end with "Environment ready". If Python is older than 3.10 the lab code will not run; Python 3.12 is the tested version. Activate the environment again (`source .venv/bin/activate`) in every new terminal.

## First run

```bash
python run_lab.py --scenario nominal --mode independent --out results/baseline
```

Open `results/baseline/replay.html` in a browser. Collision warnings on the terminal are expected for this unsafe baseline. Then continue with `ASSIGNMENT.md`.

## Secondary alternatives

A Linux virtual machine or WSL 2 running Ubuntu 24.04 can follow these same steps inside Linux. These routes are not recommended as a first choice and receive limited troubleshooting support. The browser replay works in any desktop browser, including the Windows or macOS host browser when the result directory is reachable from it. The optional `--gui` flag needs a working desktop and is never required.
