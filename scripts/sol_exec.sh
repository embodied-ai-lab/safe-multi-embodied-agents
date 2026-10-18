#!/usr/bin/env bash
# Run one command inside the course Apptainer image with the lab directory bound to /work.
# Usage: SIF=/scratch/$USER/safe-multi-embodied-agents.sif bash scripts/sol_exec.sh python run_lab.py ...
# Everything under the lab directory (source edits, results/, submission/) persists on the host.
# The image itself is read-only; writes to host bind mounts persist on the host.
set -euo pipefail
case "$(hostname -s 2>/dev/null || hostname)" in
    *login*)
        if [[ "${ALLOW_LOGIN_NODE:-0}" != "1" ]]; then
            printf '%s\n' 'Refusing to run on a login node. Request a CPU allocation first (setup/SOL.md).' >&2
            exit 2
        fi ;;
esac
: "${SIF:?Set SIF to the absolute path of the course image (see setup/SOL.md).}"
if [[ "$SIF" != /* || ! -f "$SIF" ]]; then
    printf '%s\n' "SIF must be an existing absolute path to the image, got: $SIF" >&2
    exit 2
fi
if [[ $# -eq 0 ]]; then
    printf '%s\n' 'Usage: bash scripts/sol_exec.sh python run_lab.py --scenario nominal --mode independent --out results/baseline' >&2
    exit 2
fi
if command -v module >/dev/null 2>&1; then
    # A system Apptainer on PATH does not imply that the course module is loaded.
    module load apptainer/1.4.5
fi
command -v apptainer >/dev/null 2>&1 || { printf '%s\n' 'apptainer not found. On Sol: module load apptainer/1.4.5' >&2; exit 2; }
lab_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
exec apptainer exec --cleanenv --bind "$lab_root:/work" --pwd /work "$SIF" "$@"
