"""Coordinator: passes work between the five agents and holds the human gate.

Pipeline:  Reader -> Extractor -> Verifier -> Planner -> Noter -> HUMAN APPROVAL
The coordinator never extracts or verifies anything itself; it routes state
between specialists and records every hop in the state log.
"""
from __future__ import annotations

from .agents.base import State
from .agents.reader import ReaderAgent
from .agents.extractor import ExtractorAgent
from .agents.verifier import VerifierAgent
from .agents.planner import PlannerAgent
from .agents.noter import NoterAgent


class Coordinator:
    def __init__(self):
        self.pipeline = [ReaderAgent(), ExtractorAgent(), VerifierAgent(), PlannerAgent(), NoterAgent()]

    def run(self, state: State) -> State:
        for agent in self.pipeline:
            state.note(f"[coordinator] -> {agent.name}")
            state = agent.run(state)
        return state

    def approval_gate(self, state: State, auto: bool = False,
                      input_fn=input) -> State:
        """The human decides each deadline. The agents only propose."""
        for item in state.planned:
            dl = item["deadline"]
            if auto:
                dl.approved = None  # stays 'waiting', demo never auto-approves
                continue
            print(f"\nApprove this deadline?")
            print(f"  course : {dl.course}")
            print(f"  what   : {dl.what}")
            print(f"  due    : {dl.due}")
            print(f"  proof  : \"{dl.quote}\" (from '{dl.mail_subject}')")
            ans = input_fn("  [y]es / [n]o / [s]kip: ").strip().lower()
            dl.approved = True if ans.startswith("y") else (False if ans.startswith("n") else None)
            state.note(f"[gate] human {'approved' if dl.approved else 'rejected/skipped'}: {dl.what[:50]}")
        return state
