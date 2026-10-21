from .base import Agent, State
from ..tools.core import verify_quote, detect_injection


class VerifierAgent(Agent):
    """Two checks before anything reaches the student:
    1. the quote is verbatim in the mail (no hallucinated deadlines)
    2. the mail carries no prompt-injection style instructions
    """
    name = "verifier"

    def run(self, state: State) -> State:
        by_subject = {m.subject: m for m in state.mails}
        for dl in state.extracted:
            mail = by_subject[dl.mail_subject]
            injections = detect_injection(mail)
            if injections:
                state.rejected.append({"sentence": dl.quote,
                                       "reason": f"prompt-injection flags: {injections}",
                                       "stage": "verifier"})
                state.note(f"[verifier] BLOCKED '{mail.subject}': injection patterns {injections}")
                continue
            if not verify_quote(mail, dl.quote):
                state.rejected.append({"sentence": dl.quote,
                                       "reason": "quote not verbatim in mail",
                                       "stage": "verifier"})
                state.note(f"[verifier] rejected (quote mismatch): {dl.quote[:60]}")
                continue
            state.verified.append(dl)
            state.note(f"[verifier] verified: {dl.course} due {dl.due}")
        return state
