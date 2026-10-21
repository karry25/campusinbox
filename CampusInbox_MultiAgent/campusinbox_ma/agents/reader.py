from .base import Agent, State
from ..tools.core import read_date_header, find_deadline_sentences


class ReaderAgent(Agent):
    """Reads each mail: date header + candidate deadline sentences."""
    name = "reader"

    def run(self, state: State) -> State:
        for mail in state.mails:
            ref = read_date_header(mail)
            sentences = find_deadline_sentences(mail)
            state.note(f"[reader] '{mail.subject}': ref date {ref}, "
                       f"{len(sentences)} candidate sentence(s)")
            for s in sentences:
                state.candidates.append({"mail": mail, "sentence": s, "ref": ref})
        return state
