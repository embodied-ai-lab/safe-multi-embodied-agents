"""The required four scenarios by three policies at seed 2026, plus optional extra seeds."""
import argparse
import csv
import json
from pathlib import Path
import sys

from cavlab import policies
from cavlab.simulation import ROOT, run

SCENARIOS = ("nominal", "slow_car", "delayed_grant", "lossy")
MODES = ("independent", "lease", "robust")
COLUMNS = ("scenario", "mode", "seed", "completed", "exclusion_violation_steps",
           "exclusion_violation_seconds", "max_zone_occupancy", "collision_pair_count",
           "teleports", "last_clear_time", "all_clear_time", "max_wait_seconds",
           "expired_grants_rejected", "dropped_messages", "simulation_end", "step_seconds",
           "wall_seconds", "planner_wall_seconds", "simulator", "python", "platform",
           "planner", "speed_mode")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="New directory for comparison.csv and 12 runs")
    parser.add_argument("--seeds", nargs="+", type=int, default=[2026])
    args = parser.parse_args()
    try:
        policies.check_implementation()
    except NotImplementedError as error:
        print(f"Student implementation required before the matrix can run: {error}", file=sys.stderr)
        return 2
    out = Path(args.out)
    try:
        out.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print("Output directory already exists. Choose a new --out path.", file=sys.stderr)
        return 2
    rows = []
    for seed in args.seeds:
        for scenario in SCENARIOS:
            config = json.loads((ROOT / "scenarios" / (scenario + ".json")).read_text())
            for mode in MODES:
                result = run(config, mode, seed, out / f"{scenario}-{mode}-{seed}")
                rows.append({k: result.get(k) for k in COLUMNS})
                print(f"{scenario:14s} {mode:12s} seed {seed}  completed {result['completed']}/3"
                      f"  overlap {result['exclusion_violation_seconds']:.1f} s"
                      f"  collision pairs {result['collision_pair_count']}"
                      f"  max wait {result['max_wait_seconds']}  all clear {result['all_clear_time']}")
    with (out / "comparison.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {out / 'comparison.csv'} and {len(rows)} result directories.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
