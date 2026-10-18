"""Run one scenario with one policy: python run_lab.py --help."""
import argparse
import json
from pathlib import Path
import sys

from cavlab.simulation import ROOT, run


def main():
    parser = argparse.ArgumentParser(description="Safe Multi-Embodied Agents: three connected vehicles and one coordinator in SUMO")
    parser.add_argument("--scenario", default="nominal",
                        help="nominal, slow_car, delayed_grant, lossy, or a JSON path")
    parser.add_argument("--mode", choices=["independent", "lease", "robust"], default="robust")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--out", required=True, help="New result directory, never overwritten")
    parser.add_argument("--planner", default="rule", help="rule, replay, or module:factory")
    parser.add_argument("--planner-file", type=Path, help="JSON rows for --planner replay")
    parser.add_argument("--gui", action="store_true", help="Optional SUMO GUI, needs a desktop")
    parser.add_argument("--lease-seconds", type=float, help="Start window (robust) or lease (lease)")
    parser.add_argument("--loss", type=float, help="Override message loss probability")
    parser.add_argument("--delay", type=float, help="Override one-way message delay in seconds")
    args = parser.parse_args()
    path = Path(args.scenario)
    if not path.is_file():
        path = ROOT / "scenarios" / (args.scenario + ".json")
    if not path.is_file():
        parser.error(f"Unknown scenario {args.scenario!r}. Use a name under scenarios/ or a JSON path.")
    config = json.loads(path.read_text())
    if args.lease_seconds is not None:
        if args.lease_seconds <= 0:
            parser.error("--lease-seconds must be positive")
        config["lease_seconds"] = args.lease_seconds
    if args.loss is not None:
        if not 0 <= args.loss <= 1:
            parser.error("--loss must be between 0 and 1")
        config.setdefault("network", {})["loss"] = args.loss
    if args.delay is not None:
        if args.delay < 0:
            parser.error("--delay must be nonnegative")
        config.setdefault("network", {})["delay"] = args.delay
    try:
        result = run(config, args.mode, args.seed, args.out, args.planner,
                     args.planner_file, args.gui)
    except NotImplementedError as error:
        print(f"Student implementation required: {error}", file=sys.stderr)
        return 2
    except FileExistsError:
        print("Result directory already exists. Choose a new --out path.", file=sys.stderr)
        return 2
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    out = Path(args.out)
    print(f"Wrote {out}/summary.json, trajectory.csv, events.jsonl, metadata.json, sumo.log "
          f"and {out}/replay.html (open it in a browser).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
