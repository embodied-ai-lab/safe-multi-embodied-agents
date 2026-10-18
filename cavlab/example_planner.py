"""Example of a custom planner loaded with --planner cavlab.example_planner:make_planner.

It proposes a lower cruising speed while approaching the gate and full speed
once the car is crossing. It uses only the car's own observation. The gate,
grant checks, and speed bounds stay outside the planner, so replacing it
cannot change who is allowed to enter.
"""
from .planners import Proposal


class CautiousPlanner:
    def propose(self, observation):
        if observation.phase in {"approach", "waiting"}:
            return Proposal(4.0)
        return Proposal(6.0)


def make_planner():
    return CautiousPlanner()
