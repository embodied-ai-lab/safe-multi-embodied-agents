"""The three graded functions. Infrastructure and unsafe baselines are supplied."""
from .protocol import Message, Reservation


def choose_request(pending: list[Message]) -> Message | None:
    """Oldest original request first, then vehicle ID for a deterministic tie.

    Retries retain the original request timestamp. Do not modify pending.
    """
    raise NotImplementedError("TODO: choose_request")


def grant_is_usable(grant: Message, vehicle: str, request_id: str,
                    retired_epoch: int, now: float) -> bool:
    """Check identity, request, monotonic epoch, and half-open start window.

    Call only while stopped at the gate. Entry commitment occurs at this check.
    Once committed, the car keeps its reservation until its rear has cleared.
    """
    raise NotImplementedError("TODO: grant_is_usable")


def release_matches(active: Reservation | None, message: Message) -> bool:
    """Only a matching RELEASE can end a reservation. Time alone cannot.

    'cleared' means the car's rear passed the exit. 'expired' means the stopped
    car rejected the grant and retired that epoch without committing to entry.
    A sender ID here is a trusted simulation label, not cryptographic proof.
    """
    raise NotImplementedError("TODO: release_matches")


def check_implementation():
    """Fail explicitly for unfinished work before launching the simulator."""
    choose_request([])
    grant_is_usable(Message("GRANT", "RSU", "A", "A:1", 0, 1, 1),
                    "A", "A:1", 0, 0)
    release_matches(None, Message("RELEASE", "A", "RSU", "A:1", 0))
