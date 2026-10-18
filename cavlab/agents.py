"""Independent state for each car and the roadside coordinator (RSU)."""
from . import policies
from .protocol import Message, Reservation


class Coordinator:
    def __init__(self, mode, lease_seconds, log):
        self.mode = mode
        self.lease_seconds = lease_seconds
        self.active = None
        self.pending = {}
        self.completed = set()
        self.retired = {}
        self.epoch = 0
        self.last_grant_send = -100.0
        self.log = log

    def tick(self, now, inbox, bus):
        if self.mode == "independent":
            return
        for m in inbox:
            if m.kind == "REQUEST" and m.sender not in self.completed:
                if not self.active or m.sender != self.active.vehicle:
                    self.pending.setdefault(m.sender, m)
            elif m.kind == "RELEASE":
                matches = (policies.release_matches(self.active, m)
                           if self.mode == "robust" else
                           self.active is not None and m.epoch == self.active.epoch
                           and m.sender == self.active.vehicle)
                if matches:
                    self.log(now, "reservation_released", "RSU", epoch=m.epoch,
                             vehicle=m.sender, reason=m.reason)
                    self.retired[m.epoch] = (m.sender, m.request_id, m.reason)
                    self.active = None
                    if m.reason == "cleared":
                        self.completed.add(m.sender)
                        self.pending.pop(m.sender, None)
                if self.retired.get(m.epoch) == (m.sender, m.request_id, m.reason):
                    bus.send(Message("ACK", "RSU", m.sender, m.request_id, now,
                                     m.epoch, reason=m.reason), now)
        if (self.mode == "lease" and self.active is not None
                and now >= self.active.deadline):
            self.log(now, "lease_timeout", "RSU", epoch=self.active.epoch,
                     vehicle=self.active.vehicle)
            self.active = None
        if self.active is None and self.pending:
            candidates = list(self.pending.values())
            m = (policies.choose_request(candidates) if self.mode == "robust"
                 else min(candidates, key=lambda x: (x.created, x.sender)))
            if m is not None:
                self.pending.pop(m.sender)
                self.epoch += 1
                self.active = Reservation(m.sender, m.request_id, self.epoch,
                                          now, now + self.lease_seconds)
                self.log(now, "reservation_granted", "RSU", vehicle=m.sender,
                         epoch=self.epoch, deadline=self.active.deadline)
                self.last_grant_send = -100.0
        if self.active and now - self.last_grant_send >= 0.5 - 1e-9:
            # Retransmit the SAME token and deadline. Never renew by retransmission.
            bus.send(self.active.grant(), now)
            self.last_grant_send = now


class VehicleAgent:
    def __init__(self, vehicle, mode, planner, log):
        self.vehicle = vehicle
        self.mode = mode
        self.planner = planner
        self.request_id = f"{vehicle}:1"
        self.phase = "approach"
        self.request_time = None
        self.last_request = -100.0
        self.retired_epoch = 0
        self.token = None
        self.release_pending = {}
        self.last_release = -100.0
        self.log = log

    def tick(self, now, at_gate, cleared, inbox, bus):
        if self.phase == "approach" and at_gate:
            self.phase = "waiting"
            self.request_time = now
            self.log(now, "arrive_gate", self.vehicle)
        if self.phase == "crossing" and cleared:
            self.phase = "done"
            self.log(now, "rear_cleared", self.vehicle,
                     epoch=self.token.epoch if self.token else 0)
            if self.token:
                self.release_pending[self.token.epoch] = "cleared"
                self.retired_epoch = max(self.retired_epoch, self.token.epoch)
        for m in inbox:
            if (m.kind == "ACK" and m.sender == "RSU"
                    and m.request_id == self.request_id
                    and self.release_pending.get(m.epoch) == m.reason):
                self.release_pending.pop(m.epoch, None)
            if m.kind != "GRANT" or self.phase != "waiting":
                continue
            usable = (policies.grant_is_usable(m, self.vehicle, self.request_id,
                                              self.retired_epoch, now)
                      if self.mode == "robust" else m.recipient == self.vehicle)
            if usable:
                self.token = m
                self.phase = "crossing"
                self.log(now, "commit_entry", self.vehicle, epoch=m.epoch)
            elif (m.sender == "RSU" and m.recipient == self.vehicle
                  and m.request_id == self.request_id and m.epoch > self.retired_epoch
                  and now >= m.deadline):
                # Retire BEFORE release so delayed copies cannot authorize entry.
                self.retired_epoch = m.epoch
                self.release_pending[m.epoch] = "expired"
                self.log(now, "reject_expired_grant", self.vehicle, epoch=m.epoch)
        if self.phase == "waiting":
            if self.mode == "independent":
                self.phase = "crossing"
                self.log(now, "commit_entry", self.vehicle, epoch=0)
            elif now - self.last_request >= 0.5 - 1e-9:
                bus.send(Message("REQUEST", self.vehicle, "RSU", self.request_id,
                                 self.request_time), now)
                self.last_request = now
        if now - self.last_release >= 0.5 - 1e-9:
            for epoch, reason in self.release_pending.items():
                bus.send(Message("RELEASE", self.vehicle, "RSU", self.request_id,
                                 now, epoch, reason=reason), now)
            self.last_release = now
