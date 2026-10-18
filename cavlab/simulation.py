"""SUMO is the physical plant. Agents see ego observations and delivered messages.

Observation boundary enforced in this module:
- A car agent receives its own road, lane position, and speed, plus the
  messages delivered to it. It never reads another car's state.
- The coordinator receives protocol messages only.
- The monitor in the main loop reads global state for evaluation. Nothing it
  computes flows back into an agent, a planner, or a speed command.

Time: the simulation clock advances only through traci.simulationStep(). Message
delays are expressed in simulated seconds (see network.py); nothing sleeps.
``wall_seconds`` in the summary is local execution time and is not comparable
between machines.
"""
import contextlib
import csv
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

from .agents import Coordinator, VehicleAgent
from .network import MessageBus
from .planners import Observation, load_planner, validated_speed
from . import policies

ROOT = Path(__file__).resolve().parents[1]
ROUTES = {"A": ("W_in", "E_out"), "B": ("S_in", "N_out"), "C": ("E_in", "W_out")}
JUNCTION = "J"             # the single intersection node in network/intersection.nod.xml
DT = 0.1                   # simulation step, seconds
CAR_LENGTH = 4.5           # matches the vType in network/cars.rou.xml
CLEARANCE = 0.5            # extra rear margin before a car counts as cleared
ACCEL = 2.0                # controller acceleration bound, m/s^2
BRAKE = 4.0                # controller braking bound, m/s^2
MAX_SPEED = 6.0            # controller speed bound, m/s
GATE_OFFSET = 1.0          # the gate is one meter before the incoming lane ends
GATE_TOLERANCE = 0.03      # meters from the gate that still count as "at the gate"
STOPPED_SPEED = 0.1        # m/s that still counts as stopped
SPEED_MODE = 96            # SUMO speed mode "all checks off": bits 5 and 6 set, bits 0-4 clear
LANE_CHANGE_MODE = 0       # no lane changes
SUMO_OPTIONS = ["--step-length", str(DT), "--step-method.ballistic", "false",
                "--collision.action", "warn", "--collision.check-junctions", "true",
                "--time-to-teleport", "-1", "--no-step-log", "true",
                "--duration-log.disable", "true"]
PACKAGES = ("eclipse-sumo", "sumo-data", "traci", "sumolib")
_launches = 0


def package_versions():
    """Installed versions of the pinned packages, for metadata.json. eclipse-sumo and
    sumo-data are absent on the external-SUMO route (setup/MACOS.md), where the
    executables come from PATH or SUMO_HOME; they are recorded as None, not an error."""
    versions = {}
    for name in PACKAGES:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def binary(name):
    """Locate a SUMO executable: this Python environment, then PATH, then SUMO_HOME/bin."""
    candidates = [Path(sys.executable).parent / name]
    found = shutil.which(name)
    if found:
        candidates.append(Path(found))
    if os.environ.get("SUMO_HOME"):
        candidates.append(Path(os.environ["SUMO_HOME"]) / "bin" / name)
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise RuntimeError(f"{name} not found. Activate the environment, install requirements.txt, "
                       "and run: python check_environment.py")


def build_network():
    net = ROOT / "network"
    target = net / "intersection.net.xml"
    if not target.exists():
        subprocess.run([binary("netconvert"), "--node-files", str(net / "intersection.nod.xml"),
                        "--edge-files", str(net / "intersection.edg.xml"),
                        "--connection-files", str(net / "intersection.con.xml"),
                        "--offset.disable-normalization", "true", "--output-file", str(target)],
                       check=True, capture_output=True, text=True)
    return target


def zone_state(road, lane_position, incoming, outgoing, gate):
    """Classify one car from its own road and front-bumper lane position.

    Returns (distance_to_gate, clear, inside). distance_to_gate is -1 once the
    car has left its incoming lane. clear means the rear plus CLEARANCE has
    passed the end of the junction on the outgoing lane. inside means the car
    occupies the conservative conflict zone: its front is on a junction-internal
    lane, or it is on the outgoing lane and not yet clear.
    """
    distance = gate - lane_position if road == incoming else -1.0
    clear = road == outgoing and lane_position >= CAR_LENGTH + CLEARANCE
    inside = road.startswith(f":{JUNCTION}_") or (road == outgoing and not clear)
    return distance, clear, inside


def approach_speed(speed, desired, distance):
    """Semi-implicit Euler: reserve one next step plus braking distance.

    d >= v_next*dt + v_next^2/(2*b). A stopped car stays before the gate.
    The numerical bound is used only before entry commitment.
    """
    safe = max(0.0, -BRAKE * DT + math.sqrt((BRAKE * DT) ** 2
                                           + 2 * BRAKE * max(0.0, distance)))
    target = min(desired, safe)
    return max(0.0, speed - BRAKE * DT, min(target, speed + ACCEL * DT))


def crossing_speed(speed, desired):
    """Bounded acceleration and braking once the car has committed to cross."""
    return max(0.0, speed - BRAKE * DT, min(desired, speed + ACCEL * DT))


def sumo_command(net, out, gui=False):
    command = [binary("sumo-gui" if gui else "sumo"), "-n", str(net),
               "-r", str(ROOT / "network" / "cars.rou.xml"), *SUMO_OPTIONS,
               "--error-log", str(out / "sumo.log")]
    if gui:
        command += ["--start", "--quit-on-end"]
    return command


def launch(command, seed):
    """Start SUMO on a free TraCI port and connect with a short poll instead of TraCI's
    one-second retry wait. Returns the connection label."""
    import traci
    from sumolib.miscutils import getFreeSocketPort
    global _launches
    _launches += 1
    label = f"cav-{os.getpid()}-{_launches}"
    port = getFreeSocketPort()
    process = subprocess.Popen(command + ["--seed", str(seed), "--remote-port", str(port)],
                               stdout=subprocess.DEVNULL)
    try:
        with contextlib.redirect_stdout(io.StringIO()):   # TraCI prints retry notices to stdout
            traci.connect(port=port, numRetries=600, proc=process, waitBetweenRetries=0.05,
                          label=label)
        traci.switch(label)
    except Exception:
        process.kill()
        raise
    return label


def read_geometry(traci):
    """Lane shapes and the junction polygon as SUMO reports them, for the replay page."""
    import sumolib.geomhelper as geom
    edges = {edge for pair in ROUTES.values() for edge in pair}
    lanes = {}
    for lane_id in traci.lane.getIDList():
        if traci.lane.getEdgeID(lane_id) in edges or lane_id.startswith(f":{JUNCTION}_"):
            lanes[lane_id] = dict(shape=[[round(x, 2), round(y, 2)] for x, y in traci.lane.getShape(lane_id)],
                                  width=traci.lane.getWidth(lane_id))
    gates = {}
    for vehicle, (incoming, _) in ROUTES.items():
        shape = traci.lane.getShape(incoming + "_0")
        x, y = geom.positionAtShapeOffset(shape, traci.lane.getLength(incoming + "_0") - GATE_OFFSET)
        gates[vehicle] = [round(x, 2), round(y, 2)]
    junction = [[round(x, 2), round(y, 2)] for x, y in traci.junction.getShape(JUNCTION)]
    return dict(junction=junction, lanes=lanes, gates=gates)


def launch_check():
    """One headless SUMO step over the lab network, for check_environment.py."""
    import tempfile
    import traci
    with tempfile.TemporaryDirectory() as tmp:
        label = launch(sumo_command(build_network(), Path(tmp)), 1)
        try:
            traci.simulationStep()
            present = sorted(traci.vehicle.getIDList())
            version = traci.getVersion()[1]
        finally:
            traci.close()
    return f"{version} started, {len(present)} vehicles inserted"


def run(config, mode, seed, output, planner="rule", planner_file=None, gui=False):
    import traci
    if mode == "robust":
        policies.check_implementation()
    out = Path(output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    events = []
    frames = []

    def log(now, event, actor, **data):
        events.append(dict(time=round(now, 6), event=event, actor=actor, **data))

    bus = MessageBus(config.get("network", {}), seed, log)
    rsu = Coordinator(mode, config.get("lease_seconds", 4.0), log)
    cars = {v: VehicleAgent(v, mode, load_planner(planner, planner_file), log) for v in ROUTES}
    net = build_network()
    command = sumo_command(net, out, gui)
    wall_start = time.perf_counter()
    planner_wall = 0.0
    started = False
    violation_steps = 0
    max_occupancy = 0
    collision_pairs = set()
    teleports = 0
    now = 0.0
    try:
        launch(command, seed)
        started = True
        geometry = read_geometry(traci)
        traci.simulationStep()
        gates = {v: traci.lane.getLength(edges[0] + "_0") - GATE_OFFSET for v, edges in ROUTES.items()}
        configured = set()
        for _ in range(int(config.get("horizon", 60) / DT)):
            now = traci.simulation.getTime()
            inbox = bus.deliver(now)
            rsu.tick(now, inbox["RSU"], bus)
            present = set(traci.vehicle.getIDList())
            occupied = []
            for v, car in cars.items():
                if v not in present:
                    car.tick(now, False, False, inbox[v], bus)
                    continue
                if v not in configured:
                    # Disable SUMO's own safety checks so they cannot rescue a bad
                    # coordination policy. Our controller bounds acceleration.
                    traci.vehicle.setSpeedMode(v, SPEED_MODE)
                    traci.vehicle.setLaneChangeMode(v, LANE_CHANGE_MODE)
                    configured.add(v)
                road = traci.vehicle.getRoadID(v)
                pos = traci.vehicle.getLanePosition(v)
                speed = traci.vehicle.getSpeed(v)
                incoming, outgoing = ROUTES[v]
                distance, clear, inside = zone_state(road, pos, incoming, outgoing, gates[v])
                if inside:
                    occupied.append(v)
                at_gate = road == incoming and distance <= GATE_TOLERANCE and speed <= STOPPED_SPEED
                car.tick(now, at_gate, clear, inbox[v], bus)
                observation = Observation(v, now, speed, distance, car.phase)
                planner_start = time.perf_counter()
                desired = validated_speed(car.planner.propose(observation))
                planner_wall += time.perf_counter() - planner_start
                if config.get("slow_car") == v and inside:
                    desired = min(desired, config.get("slow_speed", 0.8))
                if car.phase in {"approach", "waiting"}:
                    command_speed = approach_speed(speed, desired, distance)
                else:
                    command_speed = crossing_speed(speed, desired)
                traci.vehicle.setSpeed(v, command_speed)
                x, y = traci.vehicle.getPosition(v)
                frames.append(dict(time=round(now, 6), vehicle=v, x=x, y=y,
                                   angle=traci.vehicle.getAngle(v), speed=speed,
                                   command_speed=command_speed, road=road, lane_position=pos,
                                   phase=car.phase, occupied=int(inside),
                                   epoch=car.token.epoch if car.token else 0,
                                   distance_to_gate=round(distance, 3)))
            max_occupancy = max(max_occupancy, len(occupied))
            if len(occupied) > 1:
                violation_steps += 1
                log(now, "exclusion_violation", "monitor", vehicles=occupied)
            for collision in traci.simulation.getCollisions():
                pair = tuple(sorted((collision.collider, collision.victim)))
                if pair not in collision_pairs:
                    log(now, "collision_pair", "monitor", vehicles=pair)
                collision_pairs.add(pair)
            teleports += len(traci.simulation.getStartingTeleportIDList())
            done = all(car.phase == "done" for car in cars.values())
            if done and (mode != "robust" or all(not c.release_pending for c in cars.values())):
                break
            traci.simulationStep()
        version = traci.getVersion()[1]
    finally:
        if started:
            traci.close()
    arrivals = {e["actor"]: e["time"] for e in events if e["event"] == "arrive_gate"}
    commits = {e["actor"]: e["time"] for e in events if e["event"] == "commit_entry"}
    clears = {e["actor"]: e["time"] for e in events if e["event"] == "rear_cleared"}
    wait = {v: round(commits[v] - arrivals[v], 6) for v in commits}
    summary = dict(scenario=config["name"], mode=mode, seed=seed, completed=len(clears),
                   exclusion_violation_steps=violation_steps,
                   exclusion_violation_seconds=round(violation_steps * DT, 6),
                   max_zone_occupancy=max_occupancy, collision_pair_count=len(collision_pairs),
                   collision_pairs=sorted(collision_pairs), teleports=teleports,
                   last_clear_time=max(clears.values()) if clears else None,
                   all_clear_time=max(clears.values()) if len(clears) == 3 else None,
                   wait_seconds=wait, max_wait_seconds=max(wait.values()) if wait else None,
                   expired_grants_rejected=sum(e["event"] == "reject_expired_grant" for e in events),
                   dropped_messages=sum(e["event"] == "drop" for e in events),
                   simulation_end=now, step_seconds=DT,
                   wall_seconds=round(time.perf_counter() - wall_start, 3),
                   planner_wall_seconds=round(planner_wall, 3),
                   simulator=version, python=platform.python_version(), platform=platform.platform(),
                   planner=planner, speed_mode=SPEED_MODE)
    metadata = dict(config=config, mode=mode, seed=seed, planner=planner,
                    planner_file=str(planner_file) if planner_file else None, summary=summary,
                    controller=dict(step_seconds=DT, max_speed=MAX_SPEED, accel=ACCEL, brake=BRAKE,
                                    car_length=CAR_LENGTH, clearance=CLEARANCE, gate_offset=GATE_OFFSET,
                                    gate_tolerance=GATE_TOLERANCE, stopped_speed=STOPPED_SPEED),
                    sumo=dict(version=version, speed_mode=SPEED_MODE, lane_change_mode=LANE_CHANGE_MODE,
                              options=SUMO_OPTIONS, route_file="network/cars.rou.xml",
                              network_file="network/intersection.net.xml"),
                    packages=package_versions(),
                    geometry=geometry)
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    columns = ["time", "vehicle", "x", "y", "angle", "speed", "command_speed", "road",
               "lane_position", "phase", "occupied", "epoch", "distance_to_gate"]
    with (out / "trajectory.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(frames)
    from .replay import make_replay
    make_replay(out, frames, events, summary, geometry)
    return summary
