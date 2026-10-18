#!/usr/bin/env bash
# Build the course Apptainer image from containers/Apptainer.def and record its checksum.
# Usage (inside a CPU allocation on Sol, or on any Linux host with Apptainer):
#   bash scripts/build_image.sh [/output/path/safe-multi-embodied-agents.sif]
# Tries a plain build first, then --fakeroot. Neither uses host sudo. If both are
# rejected on this system, use the instructor-provided image instead.
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
case "$(hostname -s 2>/dev/null || hostname)" in
    *login*) echo "Refusing to build on a login node. Use sbatch scripts/sol_build.sbatch or a CPU allocation." >&2; exit 2 ;;
esac
if command -v module >/dev/null 2>&1; then
    # Sol also has /usr/bin/apptainer; select the documented version explicitly.
    module load apptainer/1.4.5
    # SIF builds need mksquashfs, which Sol provides through a module.
    command -v mksquashfs >/dev/null 2>&1 || module load squashfs-4.6.1-gcc-11.2.0 2>/dev/null || module load squashfs 2>/dev/null || true
fi
command -v apptainer >/dev/null 2>&1 || { echo "apptainer not found. On Sol: module load apptainer/1.4.5" >&2; exit 2; }
output="${1:-${SIF:-/scratch/${USER}/safe-multi-embodied-agents.sif}}"
mkdir -p "$(dirname "$output")"
export APPTAINER_CACHEDIR="${APPTAINER_CACHEDIR:-${SCRATCH:-/scratch/${USER}}/.apptainer-cache}"
export APPTAINER_TMPDIR="${APPTAINER_TMPDIR:-${SCRATCH:-/scratch/${USER}}/.apptainer-tmp}"
mkdir -p "$APPTAINER_CACHEDIR" "$APPTAINER_TMPDIR"
cd "$root"
built=0
for flags in "" "--fakeroot"; do
    echo "apptainer build ${flags} ${output} containers/Apptainer.def"
    # shellcheck disable=SC2086
    if apptainer build --force ${flags} "$output" containers/Apptainer.def; then built=1; break; fi
    echo "build with flags '${flags}' failed; trying the next route" >&2
done
test "$built" = 1 || { echo "Image build failed. Use the instructor-provided image (setup/SOL.md)." >&2; exit 1; }
apptainer test "$output"
sha256sum "$output" | tee "${output}.sha256"
{ echo "built: $(date -u +%Y-%m-%dT%H:%M:%SZ) on $(hostname)"; apptainer --version;
  echo "recipe sha256: $(sha256sum containers/Apptainer.def | cut -d' ' -f1)";
  echo "requirements sha256: $(sha256sum requirements.txt | cut -d' ' -f1)"; } | tee "${output}.build.txt"
echo "Image ready: $output"
