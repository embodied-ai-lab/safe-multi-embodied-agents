"""Seeded simulated messages, including loss, delay, duplicates, and reordering."""
from dataclasses import asdict
import heapq
import random


class MessageBus:
    def __init__(self, config, seed, log):
        self.config = config
        self.random = random.Random(seed)
        self.queue = []
        self.serial = 0
        self.log = log

    def send(self, message, now):
        c = self.config
        if (c.get("drop_all_releases", False) and message.kind == "RELEASE"
                or self.random.random() < c.get("loss", 0.0)):
            self.log(now, "drop", message.sender, message=asdict(message))
            return
        delay = c.get("delay", 0.05) + self.random.uniform(0, c.get("jitter", 0.0))
        if message.kind == "GRANT" and message.epoch == 1:
            delay += c.get("first_grant_extra_delay", 0.0)
        copies = 2 if self.random.random() < c.get("duplicate", 0.0) else 1
        for index in range(copies):
            self.serial += 1
            delivery = now + delay + index * c.get("duplicate_delay", 0.7)
            heapq.heappush(self.queue, (delivery, self.serial, message))
        self.log(now, "send", message.sender, message=asdict(message), copies=copies)

    def deliver(self, now):
        inbox = {who: [] for who in ("A", "B", "C", "RSU")}
        while self.queue and self.queue[0][0] <= now + 1e-9:
            _, _, message = heapq.heappop(self.queue)
            inbox[message.recipient].append(message)
            self.log(now, "deliver", message.recipient, message=asdict(message))
        return inbox
