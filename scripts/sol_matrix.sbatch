#!/usr/bin/env bash
# CPU batch job for the required 12-run comparison on ASU Sol.
# Submit from the lab directory:   sbatch scripts/sol_matrix.sbatch
# CSE 598 groups add the sweep:    sbatch --export=ALL,RUN_GRAD=1 scripts/sol_matrix.sbatch
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
out="results/sol-${SLURM_JOB_ID}"
bash scripts/sol_exec.sh python check_environment.py --report "${out}-environment.json"
bash scripts/sol_exec.sh python run_matrix.py --out "$out"
if [[ "${RUN_GRAD:-0}" == "1" ]]; then
    for w in 05:0.5 1:1 2:2 4:4; do
        bash scripts/sol_exec.sh python run_lab.py --scenario nominal --mode robust --seed 2026 \
            --delay 0.8 --loss 0 --lease-seconds "${w#*:}" --out "${out}-graduate-window-${w%%:*}"
    done
fi
echo "Results are under $out. Download replay.html files to view them in a browser."
