from .base import Agent, State
from ..tools.core import preview_reminder


class PlannerAgent(Agent):
    """Groups verified deadlines by course and previews reminders.
    Proposes only - the human approval gate decides."""
    name = "planner"

    def run(self, state: State) -> State:
        for dl in sorted(state.verified, key=lambda d: d.due):
            reminder = preview_reminder(dl)
            state.planned.append({"deadline": dl, "reminder": reminder})
            state.note(f"[planner] proposed: {dl.course} | {dl.what[:50]} | {dl.due}")
        return state
