"""Agent base + shared state passed between agents by the coordinator."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..tools.core import Mail, Deadline


@dataclass
class State:
    """The blackboard the agents read and write. Everything is traceable."""
    mails: list[Mail] = field(default_factory=list)
    candidates: list[dict] = field(default_factory=list)   # reader output
    extracted: list[Deadline] = field(default_factory=list) # extractor output
    verified: list[Deadline] = field(default_factory=list)  # verifier output
    rejected: list[dict] = field(default_factory=list)
    planned: list[dict] = field(default_factory=list)       # planner output
    log: list[str] = field(default_factory=list)

    def note(self, msg: str) -> None:
        self.log.append(msg)


class Agent:
    name = "agent"

    def run(self, state: State) -> State:
        raise NotImplementedError
