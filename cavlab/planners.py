"""Replaceable behavior proposals, separate from permission to enter.

A planner answers one question for one car: given this car's own observation,
what longitudinal speed does it propose? It never sees other cars, the
coordinator's state, or the evaluation monitor. The vehicle agent decides
whether the car may enter, and the controller in simulation.py bounds the
proposal by the gate, acceleration, braking, and speed limits.

To plug in your own component, write a module with a zero-argument factory
that returns an object with ``propose(observation) -> Proposal`` and run
``python run_lab.py --planner your_module:make_planner``. See
cavlab/example_planner.py. The call is synchronous: a slow model call pauses
simulated time rather than modeling inference latency.
"""
from dataclasses import dataclass
import importlib
import json
import math
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class Observation:
    vehicle: str
    time: float
    speed: float
    distance_to_gate: float
    phase: str


@dataclass(frozen=True)
class Proposal:
    target_speed: float


class Planner(Protocol):
    def propose(self, observation: Observation) -> Proposal: ...


class RulePlanner:
    """CPU placeholder for a driving decision component. No learned inference."""
    def propose(self, observation):
        return Proposal(6.0)


class ReplayPlanner:
    """Last matching timestamped speed proposal. This is synthetic replay, not inference."""
    def __init__(self, path):
        self.rows = json.loads(Path(path).read_text())
        for row in self.rows:
            if not {"vehicle", "time", "target_speed"} <= set(row):
                raise ValueError("Each replay row needs vehicle, time, and target_speed")

    def propose(self, observation):
        eligible = [r for r in self.rows if r["vehicle"] == observation.vehicle
                    and r["time"] <= observation.time]
        row = max(eligible, key=lambda r: r["time"], default={"target_speed": 6.0})
        return Proposal(float(row["target_speed"]))


def load_planner(spec, replay_path=None):
    """Return a new planner instance. Each vehicle receives its own instance."""
    if spec == "rule":
        return RulePlanner()
    if spec == "replay":
        if replay_path is None:
            raise ValueError("--planner-file is required for replay")
        return ReplayPlanner(replay_path)
    if ":" not in spec:
        raise ValueError("--planner must be rule, replay, or module:factory")
    module, factory = spec.split(":", 1)
    return getattr(importlib.import_module(module), factory)()


def validated_speed(proposal):
    value = float(proposal.target_speed)
    if not math.isfinite(value):
        raise ValueError("Planner speed must be finite")
    return min(6.0, max(0.0, value))
