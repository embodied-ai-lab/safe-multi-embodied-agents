"""Message records. Times are simulated seconds, not wall-clock timestamps."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Message:
    kind: str
    sender: str
    recipient: str
    request_id: str
    created: float
    epoch: int = 0
    deadline: float = 0.0
    reason: str = ""


@dataclass(frozen=True)
class Reservation:
    vehicle: str
    request_id: str
    epoch: int
    issued: float
    deadline: float

    def grant(self):
        return Message("GRANT", "RSU", self.vehicle, self.request_id,
                       self.issued, self.epoch, self.deadline)
