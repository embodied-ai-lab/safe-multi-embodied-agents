# Option 3: Sol with Apptainer

Use this route to run the CPU simulation inside an Ubuntu-based container on ASU's Sol supercomputer. System packages that would need `sudo` on a laptop are installed during the container build, not on Sol. Experiments run from the read-only image inside a CPU allocation; no GPU, `--nv`, writable container, or host `sudo` is involved.

## Settings you need

| Setting | Value | Note |
| --- | --- | --- |
| Slurm account | `class_cse494598fall2026` | Requested course setting; access must be confirmed for your login |
| Partition and QoS | `public`, `class` | On October 17, 2026, `public` was up and allowed the existing `class` QoS; class-account access remains unverified |
| Apptainer module | `apptainer/1.4.5` | Available on Sol on October 17, 2026; load it inside the allocation |
| SquashFS module (builds only) | `squashfs-4.6.1-gcc-11.2.0` | Available on Sol; supplies `mksquashfs` 4.6.1 |
| Course image | `safe-multi-embodied-agents.sif` | Path and SHA-256 are announced in Canvas. No image is included in the repository |

The validation login was rejected for the requested course account/partition/QoS on October 17, 2026: `Invalid account or account/partition combination specified`. This does not confirm student access. Before using this route, check the course announcement and your own association:

```bash
sacctmgr -n show assoc where user=$USER format=account%40,partition%20,qos%30
sinfo -s -p public
```

If the class account is absent or the allocation is rejected, contact course staff to resolve membership. Do not substitute another account in the course commands. Use CPU resources; do not request a GPU or an ARM/GH200 node.

Clone your private repository into `/scratch/$USER`, not into your home directory, so results and the image have room. Files there survive allocation release: your source edits, `results/`, `submission/answers.md`, and the submission ZIP. This is persistence between jobs, not a backup guarantee. Set up each new allocation with `module load apptainer/1.4.5` and `export SIF=...`; the batch scripts do this themselves. A submitting shell can pass environment variables to a job, but the image does not save shell settings.

The SIF filesystem is read-only: attempts to install into `/opt/lab` or modify system files fail. Writes to host bind mounts, including `/work`, persist on the host even when made inside `apptainer shell`. Temporary storage isolated with `--containall` disappears when that container exits; default home and temporary-directory binds should not be treated as disposable container storage. There is no virtual environment to create: the image already contains Python 3.12 and SUMO 1.28.0.

The image's headless `sumo` and `netconvert` launchers use its glibc loader explicitly. This accommodates an executable-loading failure observed with the pinned Linux wheels on Sol's 4.18 kernel; the wheels and dependency versions are unchanged. Use the supplied launchers through `scripts/sol_exec.sh` rather than invoking native binaries inside `site-packages` directly.

## 1. Get an allocation and run the checks

```bash
interactive -A class_cse494598fall2026 -p public -q class -t 60 -c 2 --mem=4G
module load apptainer/1.4.5
cd /scratch/$USER/<your private repository>
export SIF=<COURSE_PROVIDED_SIF>
sha256sum "$SIF"                 # compare with the announced checksum
bash scripts/sol_exec.sh python check_environment.py
bash scripts/sol_exec.sh python run_lab.py --scenario nominal --mode independent --out results/baseline
```

`scripts/sol_exec.sh` binds the lab directory to `/work` inside the container and runs the command there, so source changes and results land on the host. It refuses to run on a login node; request an allocation first. For any later assignment command that begins with `python`, prefix it with `bash scripts/sol_exec.sh`, or use `make PY="bash scripts/sol_exec.sh python" <target>`:

```bash
bash scripts/sol_exec.sh python run_matrix.py --out results/comparison
bash scripts/sol_exec.sh python package_submission.py --groupid <your group id>
```

Download `replay.html` files to your own computer, for example with the Sol web portal or `scp`, and open them in a browser. Each file is self-contained.

## 2. Batch execution

From the lab directory, with `SIF` exported:

```bash
sbatch scripts/sol_matrix.sbatch                          # the 12 required runs
sbatch --export=ALL,RUN_GRAD=1 scripts/sol_matrix.sbatch  # also the CSE 598 sweep
```

The job writes `results/sol-<jobid>/` plus an environment report, and the sweep directories next to it, so separate jobs never overwrite each other. The job log is `results/slurm-<jobid>.out`.

## 3. Building the image, only if no course image is provided

The recommended workflow is the instructor-built image. If you need to build one, do it in a CPU job:

```bash
sbatch scripts/sol_build.sbatch
```

The job runs `scripts/build_image.sh`, which loads the Apptainer and SquashFS modules, keeps the build cache on scratch, tries a plain `apptainer build` and then `--fakeroot`, runs the image's self-test, and writes `/scratch/$USER/safe-multi-embodied-agents.sif` with `.sha256` and `.build.txt` files next to it. The recipe is `containers/Apptainer.def`; its `%post` section performs the `apt-get` and `pip` installation with the build's privileges. An ordinary `apptainer shell` does not grant root access or make a SIF writable, so do not try to install packages that way. If both build routes are rejected on your account, use the course image or ask the course staff; do not run host `sudo` or change cluster settings.

References: [ASU Apptainer usage](https://docs.rc.asu.edu/apptainer/), [requesting resources](https://docs.rc.asu.edu/requesting-resources/), [building software](https://docs.rc.asu.edu/building-software/).
