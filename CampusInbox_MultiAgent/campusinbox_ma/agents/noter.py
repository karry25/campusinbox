from .base import Agent, State
from ..tools.core import make_note


class NoterAgent(Agent):
    """Writes a short prep note for every planned deadline.

    The Planner decides WHEN something is due; the Noter writes down WHAT the
    student should do about it (a note, not a message - nothing is sent).
    Runs after the Planner, before the human approval gate.
    """
    name = "noter"

    def run(self, state: State) -> State:
        for item in state.planned:
            dl = item["deadline"]
            note = make_note(dl)
            dl.notes.append(note)
            item["note"] = note
            state.note(f"[noter] noted: {dl.course} | {note['priority']} priority | "
                       f"first step: {note['first_step'][:50]}")
        return state
