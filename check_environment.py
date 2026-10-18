"""Check that this machine can run the lab. This is an infrastructure check only.

It reports Python, the pinned SUMO packages, the simulator executables, the lab
files, and a one-step TraCI launch. Passing means the tools are ready. It says
nothing about whether the graded functions are correct.
"""
import argparse
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
MIN_PYTHON = (3, 10)
RECOMMENDED_PYTHON = (3, 12)


def pinned_requirements():
    pins = {}
    for line in (ROOT / "requirements.txt").read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            name, version = line.split("==")
            pins[name.strip()] = version.strip()
    return pins


def find_executable(name):
    candidates = [Path(sys.executable).parent / name]
    found = shutil.which(name)
    if found:
        candidates.append(Path(found))
    if os.environ.get("SUMO_HOME"):
        candidates.append(Path(os.environ["SUMO_HOME"]) / "bin" / name)
    return next((str(c) for c in candidates if c.is_file()), None)


def command_version(executable):
    try:
        result = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as error:
        return None, str(error)
    text = (result.stdout + result.stderr).strip()
    match = re.search(r"(\d+\.\d+\.\d+)", text)
    return (match.group(1) if match else None), text.splitlines()[0] if text else ""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="Also write a JSON report to this path")
    args = parser.parse_args()
    results = []

    def record(status, name, detail):
        results.append(dict(status=status, check=name, detail=detail))
        print(f"[{status}] {name}: {detail}")

    # Python and environment
    version = sys.version_info[:3]
    text = ".".join(map(str, version))
    if version < MIN_PYTHON:
        record("FAIL", "python", f"{text} is older than the required {'.'.join(map(str, MIN_PYTHON))}")
    elif version[:2] != RECOMMENDED_PYTHON:
        record("note", "python", f"{text} (3.12 is the tested version)")
    else:
        record("ok", "python", f"{text} at {sys.executable}")
    in_venv = sys.prefix != sys.base_prefix
    record("ok" if in_venv else "note", "virtualenv",
           "active" if in_venv else "not active; the documented setup uses .venv")
    record("ok", "platform", f"{platform.system()} {platform.machine()}, {platform.platform()}")

    # Pinned packages. eclipse-sumo and sumo-data may be replaced by an external SUMO
    # installation of the same version (the macOS installer route in setup/MACOS.md).
    pins = pinned_requirements()
    expected = pins.get("eclipse-sumo")
    external = find_executable("sumo")
    external_version = command_version(external)[0] if external else None
    external_ok = external_version == expected and Path(external).parent != Path(sys.executable).parent
    for name, wanted in pins.items():
        try:
            installed = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            if name in ("eclipse-sumo", "sumo-data") and external_ok:
                record("note", f"package {name}", f"not installed, external SUMO {external_version} found at {external}")
            else:
                record("FAIL", f"package {name}", "not installed (pip install -r requirements.txt)")
            continue
        if installed != wanted:
            record("FAIL", f"package {name}", f"{installed} installed, {wanted} pinned")
        else:
            record("ok", f"package {name}", installed)
    for module in ("traci", "sumolib"):
        try:
            importlib.import_module(module)
            record("ok", f"import {module}", "importable")
        except Exception as error:  # noqa: BLE001
            record("FAIL", f"import {module}", str(error))

    # Simulator executables
    for name in ("sumo", "netconvert"):
        path = find_executable(name)
        if not path:
            record("FAIL", name, "not found in this environment, PATH, or SUMO_HOME/bin")
            continue
        found, line = command_version(path)
        if expected and found != expected:
            record("FAIL", name, f"{path} reports {found or line!r}, expected {expected}")
        else:
            record("ok", name, f"{path} ({line})")
    gui = find_executable("sumo-gui")
    record("note", "sumo-gui", f"{gui} (optional)" if gui else "not found (optional, not needed)")

    # Lab files
    for relative in ("network/intersection.net.xml", "network/cars.rou.xml", "scenarios/nominal.json",
                     "scenarios/slow_car.json", "scenarios/delayed_grant.json", "scenarios/lossy.json",
                     "cavlab/policies.py", "submission/answers_template.md"):
        exists = (ROOT / relative).is_file()
        record("ok" if exists else "FAIL", relative, "present" if exists else "missing")
    answers = (ROOT / "submission" / "answers.md").is_file()
    record("ok" if answers else "note", "submission/answers.md",
           "present" if answers else "not created yet: cp submission/answers_template.md submission/answers.md")
    try:
        (ROOT / "results").mkdir(exist_ok=True)
        probe = ROOT / "results" / ".write-test"
        probe.write_text("")
        probe.unlink()
        record("ok", "results/", "writable")
    except OSError as error:
        record("FAIL", "results/", f"not writable: {error}")

    # One-step TraCI launch, headless
    sumo = find_executable("sumo")
    if sumo and not any(r["status"] == "FAIL" and r["check"].startswith("import") for r in results):
        try:
            sys.path.insert(0, str(ROOT))
            from cavlab.simulation import launch_check
            record("ok", "traci launch", launch_check())
        except Exception as error:  # noqa: BLE001
            record("FAIL", "traci launch", f"{type(error).__name__}: {error}")

    # Graded functions: status only, never a correctness claim
    try:
        sys.path.insert(0, str(ROOT))
        from cavlab import policies
        policies.check_implementation()
        record("note", "graded functions", "implemented; this check does not test their correctness")
    except NotImplementedError as error:
        record("note", "graded functions", f"not implemented yet ({error}); expected in the starter")
    except Exception as error:  # noqa: BLE001
        record("note", "graded functions", f"raised {type(error).__name__}: {error}")

    failed = [r for r in results if r["status"] == "FAIL"]
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(dict(checks=results, ready=not failed), indent=2) + "\n")
    if failed:
        print(f"\nEnvironment is not ready: {len(failed)} check(s) failed. Fix the FAIL lines above.")
        return 1
    print("\nEnvironment ready for the lab commands. This check does not test the graded functions"
          " or any experiment result.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
