from .base import Agent, State
from ..tools.core import Deadline, parse_date, tag_course


class ExtractorAgent(Agent):
    """Turns each candidate sentence into a structured Deadline (date + course)."""
    name = "extractor"

    def run(self, state: State) -> State:
        for cand in state.candidates:
            due = parse_date(cand["sentence"], cand["ref"])
            if due is None:
                state.rejected.append({"sentence": cand["sentence"],
                                       "reason": "no parseable date",
                                       "stage": "extractor"})
                state.note(f"[extractor] dropped (no date): {cand['sentence'][:60]}")
                continue
            course = tag_course(cand["sentence"], cand["mail"].subject)
            state.extracted.append(Deadline(
                course=course, what=cand["sentence"].strip().rstrip("."),
                due=due, quote=cand["sentence"].strip(),
                mail_subject=cand["mail"].subject))
            state.note(f"[extractor] {course} deadline on {due} from "
                       f"'{cand['mail'].subject}'")
        return state
