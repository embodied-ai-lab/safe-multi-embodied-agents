"""Package the current working tree into one group ZIP, including uncommitted edits.

The archive is built from the files on disk, never from Git. It includes
submission/answers.md as answers.md at the archive root, the blank
submission/answers_template.md, the lab code, configuration, setup notes, and
everything under results/ with an allowed suffix. It excludes virtual
environments, caches, Git metadata, container images, archives, hidden files,
symbolic links, files above 25 MB, and the instructor-only directories. Every
skipped file inside the packaged trees is listed so omitted evidence is visible.

Before writing the ZIP, it checks the layout the assignment asks for: the two
Part 1 runs, the 12 comparison runs with comparison.csv, the six files of each
run, a figure under results/, and for CSE 598 the four start-window runs. These
are completeness warnings about file names and layout, never about whether a
result or an answer is correct, and they do not stop the ZIP, so partial work
can still be submitted. Only --require-grad (REQUIRE_GRAD=1) turns a missing
graduate sweep into an error.
"""
import argparse
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
LAB = "safe-multi-embodied-agents"
DIRECTORIES = {"cavlab", "network", "scenarios", "results", "setup", "containers", "scripts"}
# Root files listed here are included whatever their suffix: Makefile and LICENSE have none.
FILES = {"README.md", "ASSIGNMENT.md", "PROTOCOL.md", "SECURITY.md", "THIRD_PARTY_NOTICES.md", "requirements.txt",
         "LICENSE", "Makefile", "check_environment.py", "run_lab.py", "run_matrix.py",
         "package_submission.py"}
# Files inside DIRECTORIES must carry one of these suffixes.
SUFFIXES = {".py", ".md", ".txt", ".xml", ".json", ".jsonl", ".csv", ".html", ".log",
            ".png", ".jpg", ".jpeg", ".svg", ".pdf", ".def", ".sh", ".sbatch"}
# submission/ is excluded as a tree (drafts, old ZIPs); exactly two files are taken from it.
ANSWERS = Path("submission/answers.md")
TEMPLATE = Path("submission/answers_template.md")
EXCLUDED_PARTS = {"__pycache__", "instructor", "tests", "docs", "submission", "node_modules"}
MAX_FILE_BYTES = 25 * 1024 * 1024
FIGURE_SUFFIXES = {".png", ".jpg", ".jpeg", ".svg", ".pdf"}
RUN_FILES = ("summary.json", "events.jsonl", "trajectory.csv", "metadata.json", "sumo.log", "replay.html")
PART1_RUNS = ("part1-independent", "part1-lease")
MATRIX_RUNS = tuple(f"{scenario}-{mode}-2026" for scenario in ("nominal", "slow_car", "delayed_grant", "lossy")
                    for mode in ("independent", "lease", "robust"))
GRADUATE_RUNS = ("graduate-window-05", "graduate-window-1", "graduate-window-2", "graduate-window-4")


def select(root, target):
    """Walk the allowed trees. Returns the files to archive and the files skipped with a reason.

    rglob never descends into a symbolic link to a directory, symbolic links to files
    are skipped, and anything that resolves outside the lab directory is refused.
    """
    selected, skipped = [], []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        parts = relative.parts
        if any(p.startswith(".") or p in EXCLUDED_PARTS for p in parts):
            continue
        if path.is_symlink() or not path.is_file() or path.resolve() == target:
            continue
        root_file = len(parts) == 1 and parts[0] in FILES
        if not root_file and parts[0] not in DIRECTORIES:
            continue
        if root not in path.resolve().parents:
            skipped.append((relative, "resolves outside the lab directory"))
            continue
        if not root_file and path.suffix.lower() not in SUFFIXES:
            skipped.append((relative, f"unrecognized file type {path.suffix or '(no suffix)'}"))
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            skipped.append((relative, f"larger than {MAX_FILE_BYTES // (1024 * 1024)} MB"))
            continue
        selected.append((path, relative))
    return selected, skipped


def unlisted_top_level(root):
    """Top-level entries outside the submission layout, reported once each."""
    names = []
    for entry in sorted(root.iterdir()):
        name = entry.name
        if name.startswith(".") or name in EXCLUDED_PARTS or name in DIRECTORIES or name in FILES:
            continue
        names.append(name + "/" if entry.is_dir() else name)
    return names


def completeness(archive_names, require_grad):
    """Layout checks for the assignment's deliverables. Returns (warnings, errors).

    Presence of a file is all that is checked. A run that collided, did not
    complete, or differs from anyone else's result is still a complete run.
    """
    names = set(archive_names)

    def present(run):
        return f"results/{run}/summary.json" in names

    warnings, errors = [], []
    missing = [run for run in PART1_RUNS if not present(run)]
    if missing:
        warnings.append("Part 1: missing " + ", ".join(f"results/{run}/" for run in missing)
                        + " (python run_lab.py --scenario nominal --mode independent --out results/part1-independent,"
                        " and the same with --mode lease --out results/part1-lease)")
    if "results/comparison/comparison.csv" not in names:
        warnings.append("Part 3: results/comparison/comparison.csv is missing"
                        " (python run_matrix.py --out results/comparison)")
    missing = [run for run in MATRIX_RUNS if not present(f"comparison/{run}")]
    if missing:
        warnings.append(f"Part 3: {len(missing)} of the 12 comparison runs missing under results/comparison/: "
                        + ", ".join(missing))
    if not any(name.startswith("results/") and Path(name).suffix.lower() in FIGURE_SUFFIXES for name in names):
        warnings.append("Part 3: no figure (.png, .jpg, .svg, or .pdf) found under results/")
    incomplete = []
    for run in PART1_RUNS + tuple(f"comparison/{run}" for run in MATRIX_RUNS) + GRADUATE_RUNS:
        if present(run):
            gaps = [name for name in RUN_FILES if f"results/{run}/{name}" not in names]
            if gaps:
                incomplete.append(f"results/{run}/ lacks {', '.join(gaps)}")
    if incomplete:
        warnings.append("Run files: " + "; ".join(incomplete))
    missing = [run for run in GRADUATE_RUNS if not present(run)]
    if require_grad and missing:
        errors.append("Missing CSE 598 results: " + ", ".join(missing))
    elif 0 < len(missing) < len(GRADUATE_RUNS):
        warnings.append("CSE 598: the start-window sweep is incomplete; missing " + ", ".join(missing))
    return warnings, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--groupid", required=True, help="Group identifier, for example 05")
    parser.add_argument("--output", type=Path,
                        help=f"ZIP path. Default: submission/group<id>_{LAB}.zip")
    parser.add_argument("--require-grad", action="store_true",
                        help="CSE 598: fail unless the four start-window results are present")
    args = parser.parse_args()
    target = args.output or ROOT / "submission" / f"group{args.groupid}_{LAB}.zip"
    target = target.resolve()
    answers = ROOT / ANSWERS
    template = ROOT / TEMPLATE
    if not answers.is_file() or answers.is_symlink():
        parser.error("submission/answers.md is missing. Copy submission/answers_template.md and complete it.")
    selected, skipped = select(ROOT, target)
    selected.insert(0, (answers, Path("answers.md")))
    warnings = []
    if template.is_file() and not template.is_symlink():
        # check_environment.py expects the template, so an extracted ZIP carries it too.
        selected.append((template, TEMPLATE))
        if answers.read_bytes() == template.read_bytes():
            warnings.append("submission/answers.md is identical to the template; nothing has been filled in yet")
    else:
        warnings.append("submission/answers_template.md is missing; restore it from the template repository")
    names = [relative.as_posix() for _, relative in selected]
    summaries = [name for name in names if name.startswith("results/") and name.endswith("/summary.json")]
    if not summaries:
        parser.error("No results/*/summary.json found. Run the experiments before packaging.")
    more_warnings, errors = completeness(names, args.require_grad)
    warnings += more_warnings
    if errors:
        parser.error(" ".join(errors))
    if target.exists():
        parser.error(f"{target} already exists. Remove it or choose another --output.")
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "x", zipfile.ZIP_DEFLATED) as archive:
        for path, relative in selected:
            archive.write(path, relative.as_posix())
    for relative, reason in skipped:
        print(f"Skipped {relative}: {reason}", file=sys.stderr)
    unlisted = unlisted_top_level(ROOT)
    if unlisted:
        print("Not packaged (outside the submission layout): " + ", ".join(unlisted), file=sys.stderr)
    for warning in warnings:
        print(f"WARNING {warning}", file=sys.stderr)
    size = target.stat().st_size / (1024 * 1024)
    print(f"Created {target} with {len(selected)} files ({size:.1f} MB) from the current working tree,"
          f" including {len(summaries)} result summaries.")
    if warnings:
        print(f"{len(warnings)} completeness warning(s) above. The ZIP was still built so partial work can be"
              " submitted; ASSIGNMENT.md lists what each part needs.")
    print("Inspect it before uploading: unzip -l", target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
