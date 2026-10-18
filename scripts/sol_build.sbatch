#!/usr/bin/env bash
# CPU batch job that builds the course image on ASU Sol when no course image is provided.
# Submit from the lab directory:   sbatch scripts/sol_build.sbatch
# Output: /scratch/$USER/safe-multi-embodied-agents.sif plus .sha256 and .build.txt next to it.
# The settings below are the Fall 2026 course settings used by the other ISCPS project labs.
#SBATCH --job-name=safe-multi-embodied-agents-build
#SBATCH --account=class_cse494598fall2026
#SBATCH --partition=public
#SBATCH --qos=class
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --output=results/build-%j.out
set -euo pipefail
: "${SLURM_SUBMIT_DIR:?Submit this script with sbatch from the lab directory.}"
cd -- "$SLURM_SUBMIT_DIR"
bash scripts/build_image.sh
