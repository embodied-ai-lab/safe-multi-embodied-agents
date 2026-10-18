# Coordination protocol

## The physical rule

At most one car may occupy the conflict zone. In this lab a car occupies the zone when its front is on an internal lane of junction `J`, or when its front has entered the outgoing lane but its rear plus a 0.5 m clearance margin has not yet left the junction. The whole junction is one exclusive resource. This is intentionally more conservative than exact pairwise geometric conflict, so two cars can violate the rule without touching.

Cars stop at a gate one meter before the end of their incoming lane and request entry. A valid grant lets a stopped car commit to crossing. The car then keeps its reservation until its rear has cleared, even if the grant's start deadline passes while it is moving. A message in a log does not move a vehicle: the controller's speed command is applied to SUMO at the next simulation step, and only the recorded motion shows what happened.

## Agents and what they observe

| Agent | Observes | Sends |
| --- | --- | --- |
| Car A, B, C (one `VehicleAgent` each) | Its own road, lane position, speed, phase, and the messages delivered to it | `REQUEST`, `RELEASE` |
| Roadside coordinator `RSU` | Delivered protocol messages, its pending queue, and one current reservation | `GRANT`, `ACK` |
| Evaluation monitor (not an agent) | Every vehicle's position, for metrics only | nothing |

The coordinator never reads vehicle positions. The monitor never influences a decision. Ego sensing is idealized and the message identities are trusted labels, not authenticated sources.

## Messages

| Kind | Sender to receiver | Meaning |
| --- | --- | --- |
| `REQUEST` | Car to RSU | Request to cross. Retries keep the original request timestamp and ID |
| `GRANT` | RSU to car | Permission to commit before a start deadline, carrying a unique reservation epoch |
| `RELEASE` with `cleared` | Car to RSU | The car's rear has cleared the exit |
| `RELEASE` with `expired` | Car to RSU | The car did not commit and has permanently retired this expired token |
| `ACK` | RSU to car | Acknowledgment of one specific release |

`epoch` is a monotonically increasing reservation number assigned by the coordinator. It distinguishes grants, including several grants for the same trip. `request_id` identifies one vehicle's trip; every car makes exactly one trip. A retransmitted grant carries the same epoch, issue time, and deadline. The coordinator never renews a grant by retransmitting it.

## The three functions to implement

### `choose_request(pending)`

Return the pending request with the smallest `(created, sender)` pair, or `None` for an empty list: oldest original request first, vehicle ID as the tie-break. Do not mutate the list. The coordinator chooses only among messages it has received; it cannot account for a request still in transit.

### `grant_is_usable(grant, vehicle, request_id, retired_epoch, now)`

All of the following must hold:

- The message kind is `GRANT` and the sender is `RSU`.
- The recipient and request ID match this car and its current trip.
- The epoch is strictly greater than the greatest epoch this car has retired.
- The current simulated time satisfies `grant.created <= now < grant.deadline`.

The function is called only while the car is stopped at the gate, and its success is the moment of entry commitment. The deadline limits that commitment, not the physical crossing. A grant that arrives at or after its deadline is retired first and then cancelled with an `expired` release, so later copies of it can never authorize entry. The time check rejects a late copy on its own; the epoch check is the car's independent guarantee that it keeps the promise made in the `expired` release even if a copy claimed a different deadline.

### `release_matches(active, message)`

Return true only if there is an active reservation, the message is a `RELEASE` addressed to `RSU`, its sender, request ID, and epoch all match the active reservation, and its reason is `cleared` or `expired`. The coordinator does not release an active reservation because its deadline passed. The supplied vehicle state machine sends these reasons only when their conditions hold.

## Retries and state transitions

Requests, grants, and releases are retransmitted every 0.5 simulated seconds while needed. A car keeps retrying a release until a matching acknowledgment arrives. The coordinator remembers retired reservations so it can acknowledge duplicate releases; a duplicate old release cannot free a newer reservation.

Vehicle states are `approach`, `waiting`, `crossing`, and `done`. A usable grant moves a stopped car from `waiting` to `crossing`. Rear clearance moves it to `done`. An expired grant keeps the car in `waiting` and triggers the cancellation. Completed cars keep processing acknowledgments after they leave the visible road.

Within each 0.1 s step: queued messages that are due are delivered, the coordinator processes its inbox, each car processes its inbox and ego observation, speed commands are applied, and SUMO advances. A message sent during a step is delivered no earlier than the next step's delivery phase, even with zero configured delay, so every delay is quantized to the 0.1 s grid.

## Metrics and limits

| Metric | Interpretation |
| --- | --- |
| `exclusion_violation_seconds` | Sampled states with two or more occupants, times 0.1 s |
| `max_zone_occupancy` | Largest number of simultaneous occupants observed |
| `collision_pair_count` | Distinct vehicle pairs for which SUMO reported a collision |
| `completed` | Cars whose rear cleared before the horizon |
| `all_clear_time` | Last clearance time if all three cleared, otherwise JSON `null` |
| `wait_seconds` | Gate arrival to entry commitment, for cars that committed |
| `expired_grants_rejected` | Distinct unused expired grants retired by cars |
| `dropped_messages` | Messages the simulated network lost |
| `wall_seconds`, `planner_wall_seconds` | Local execution time, and the part spent inside planner calls. Not simulated time, not comparable between machines |

Overlap is not a collision: a collision-free trace can still violate the exclusion rule. Waiting metrics exclude cars that never committed, so always report completion together with waiting time. A zero observed violation count applies to this simulation and its sampling. It is not a proof for continuous trajectories, real roads, or arbitrary network failures.

All agents share one simulation clock, ego sensing is idealized, and message identities are trusted labels. Checking `sender == "RSU"` is not source authentication. Malicious messages, false clearance reports, coordinator restarts, and arbitrary vehicle behavior are outside this experiment. Permanent message loss can prevent progress even while the cars that remain outside obey the exclusion rule; a timeout by itself is not evidence that the space is clear.
