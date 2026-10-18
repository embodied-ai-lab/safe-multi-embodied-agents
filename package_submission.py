"""Package the current working tree into one group ZIP, including uncommitted edits.

The archive is built from the files on disk, never from Git. It includes
submission/answers.md as answers.md at the archive root, the lab code,
configuration, setup notes, and everything under results/ with an allowed
suffix. It excludes virtual environments, caches, Git metadata, container
images, hidden files, and any instructor-only directories.
"""
import argparse
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
LAB = "safe-multi-embodied-agents"
DIRECTORIES = {"cavlab", "network", "scenarios", "results", "setup", "containers", "scripts"}
FILES = {"README.md", "ASSIGNMENT.md", "PROTOCOL.md", "SECURITY.md", "THIRD_PARTY_NOTICES.md", "requirements.txt",
         "LICENSE", "Makefile", "check_environment.py", "run_lab.py", "run_matrix.py",
         "package_submission.py"}
SUFFIXES = {".py", ".md", ".txt", ".xml", ".json", ".jsonl", ".csv", ".html", ".log",
            ".png", ".jpg", ".jpeg", ".svg", ".pdf", ".def", ".sh", ".sbatch"}
EXCLUDED_PARTS = {"__pycache__", "instructor", "tests", "docs", "submission", "node_modules"}
MAX_FILE_BYTES = 25 * 1024 * 1024
GRADUATE_RUNS = ("graduate-window-05", "graduate-window-1", "graduate-window-2", "graduate-window-4")


def select(root, target):
    selected, skipped = [], []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        parts = relative.parts
        if any(p.startswith(".") or p in EXCLUDED_PARTS for p in parts):
            continue
        if path.is_symlink() or not path.is_file() or path.resolve() == target:
            continue
        if parts[0] in DIRECTORIES or (len(parts) == 1 and parts[0] in FILES):
            if path.suffix.lower() not in SUFFIXES:
                continue
            if path.stat().st_size > MAX_FILE_BYTES:
                skipped.append(relative)
                continue
            selected.append((path, relative))
    return selected, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groupid", required=True, help="Group identifier, for example 05")
    parser.add_argument("--output", type=Path,
                        help=f"ZIP path. Default: submission/group<id>_{LAB}.zip")
    parser.add_argument("--require-grad", action="store_true",
                        help="CSE 598: fail unless the four start-window results are present")
    args = parser.parse_args()
    target = args.output or ROOT / "submission" / f"group{args.groupid}_{LAB}.zip"
    target = target.resolve()
    answers = ROOT / "submission" / "answers.md"
    if not answers.is_file() or answers.is_symlink():
        parser.error("submission/answers.md is missing. Copy submission/answers_template.md and complete it.")
    selected, skipped = select(ROOT, target)
    selected.insert(0, (answers, Path("answers.md")))
    summaries = [r for _, r in selected if r.parts[0] == "results" and r.name == "summary.json"]
    if not summaries:
        parser.error("No results/*/summary.json found. Run the experiments before packaging.")
    if args.require_grad:
        missing = [run for run in GRADUATE_RUNS
                   if Path("results", run, "summary.json") not in summaries]
        if missing:
            parser.error("Missing CSE 598 results: " + ", ".join(missing))
    if target.exists():
        parser.error(f"{target} already exists. Remove it or choose another --output.")
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "x", zipfile.ZIP_DEFLATED) as archive:
        for path, relative in selected:
            archive.write(path, relative.as_posix())
    for relative in skipped:
        print(f"Skipped {relative}: larger than {MAX_FILE_BYTES // (1024 * 1024)} MB", file=sys.stderr)
    size = target.stat().st_size / (1024 * 1024)
    print(f"Created {target} with {len(selected)} files ({size:.1f} MB) from the current working tree,"
          f" including {len(summaries)} result summaries.")
    print("Inspect it before uploading: unzip -l", target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
