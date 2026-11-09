#!/usr/bin/env bash
# CPU batch job for the required 12-run comparison on ASU Sol.
# Submit from the lab directory:   sbatch scripts/sol_matrix.sbatch
# CSE 598 groups add the sweep:    sbatch --export=ALL,RUN_GRAD=1 scripts/sol_matrix.sbatch
#
# The job writes the same directories as the interactive commands in ASSIGNMENT.md, so
# `make submission GROUPID=<id> [REQUIRE_GRAD=1]` packages them without renaming:
#   results/comparison/                   comparison.csv and the 12 runs (Part 3)
#   results/graduate-window-{05,1,2,4}/   the start-window sweep (CSE 598, RUN_GRAD=1 only)
# Results are never overwritten: if any of those directories already exists, the job
# stops before running anything and names it. Move or delete the old run first, for
# example `mv results/comparison results/comparison-old`, then resubmit. Run the two
# Part 1 commands yourself inside an allocation; they are not part of this job.
# Job-specific diagnostics: results/slurm-<jobid>.out (log) and
# results/slurm-<jobid>-environment.json (environment report).
#
# The account, partition, and QoS below are the Fall 2026 course settings used by
# the other ISCPS project labs. Confirm them against the current course announcement.
#SBATCH --job-name=safe-multi-embodied-agents
#SBATCH --account=class_cse494598fall2026
#SBATCH --partition=public
#SBATCH --qos=class
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=results/slurm-%j.out
set -euo pipefail
: "${SLURM_SUBMIT_DIR:?Submit this script with sbatch from the lab directory.}"
cd -- "$SLURM_SUBMIT_DIR"
module load apptainer/1.4.5
export SIF="${SIF:-/scratch/${USER}/safe-multi-embodied-agents.sif}"
test -f "$SIF" || { echo "Missing $SIF. Set SIF to the course image or build one with sbatch scripts/sol_build.sbatch." >&2; exit 2; }
run_grad="${RUN_GRAD:-0}"
windows=(05:0.5 1:1 2:2 4:4)
destinations=(results/comparison)
if [[ "$run_grad" == "1" ]]; then
    for w in "${windows[@]}"; do destinations+=("results/graduate-window-${w%%:*}"); done
fi
existing=()
for d in "${destinations[@]}"; do
    if [[ -e "$d" ]]; then existing+=("$d"); fi
done
if [[ ${#existing[@]} -gt 0 ]]; then
    echo "Refusing to overwrite existing results: ${existing[*]}" >&2
    echo "Move or delete them first (for example: mv results/comparison results/comparison-old), then resubmit." >&2
    exit 2
fi
bash scripts/sol_exec.sh python check_environment.py --report "results/slurm-${SLURM_JOB_ID}-environment.json"
bash scripts/sol_exec.sh python run_matrix.py --out results/comparison
if [[ "$run_grad" == "1" ]]; then
    for w in "${windows[@]}"; do
        bash scripts/sol_exec.sh python run_lab.py --scenario nominal --mode robust --seed 2026 \
            --delay 0.8 --loss 0 --lease-seconds "${w#*:}" --out "results/graduate-window-${w%%:*}"
    done
fi
grad_flag=""
if [[ "$run_grad" == "1" ]]; then grad_flag=" REQUIRE_GRAD=1"; fi
echo "Wrote ${destinations[*]}. Download replay.html files to view them in a browser."
echo "Package with: make PY=\"bash scripts/sol_exec.sh python\" submission GROUPID=<id>${grad_flag}"
