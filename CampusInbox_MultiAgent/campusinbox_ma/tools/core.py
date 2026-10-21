"""Shared tool functions for CampusInbox multi-agent version.

Every tool is a small, testable function. Agents decide which tool to call;
the tools themselves never talk to each other.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

DEADLINE_CUES = (
    "deadline", "submit", "submission", "due", "last date", "by ",
    "before", "no later than", "on or before", "viva", "exam",
    "test", "quiz", "presentation", "register", "registration",
)

COURSE_KEYWORDS = {
    "Agentic AI": ("agentic", "langgraph", "langchain", "agent", "bce27pe02"),
    "DS": ("distributed", "ds lab", "rpc", "raft", "mapreduce"),
    "OOMD": ("oomd", "uml", "object oriented", "class diagram", "design pattern"),
    "Placement": ("placement", "campus drive", "interview", "aptitude", "company"),
}

INJECTION_PATTERNS = (
    r"ignore (all )?(previous|prior) instructions",
    r"system prompt",
    r"you are now",
    r"do not tell the user",
    r"forward (this|all) (mail|email)",
    r"send (the )?(user|student)? ?(data|credentials|password)",
    r"<\s*script",
    r"act as (an? )?(admin|system)",
)


@dataclass
class Mail:
    """One college mail, demo or live."""
    subject: str
    sender: str
    date_header: str
    body: str
    source: str = "demo"  # demo | gmail (read-only, untested live)

    def reference_date(self) -> date:
        """Tool: read the date header -> a real date the agent can reason with."""
        dt = parsedate_to_datetime(self.date_header)
        return dt.date()


@dataclass
class Deadline:
    course: str
    what: str
    due: date
    quote: str          # verbatim sentence from the mail, the proof
    mail_subject: str
    approved: bool | None = None   # None = waiting for the human
    notes: list = field(default_factory=list)


def read_date_header(mail: Mail) -> date:
    return mail.reference_date()


def find_deadline_sentences(mail: Mail) -> list[str]:
    """Tool: search the mail body for sentences that look like deadlines."""
    # split on newlines first so greetings never glue onto deadline lines
    chunks = []
    for line in mail.body.splitlines():
        chunks.extend(re.split(r"(?<=[.!?])\s+", line))
    sentences = [c for c in chunks if c.strip()]
    hits = []
    for s in sentences:
        low = s.lower()
        if any(cue in low for cue in DEADLINE_CUES) and _has_date_signal(s):
            hits.append(s.strip())
    return hits


def _has_date_signal(sentence: str) -> bool:
    low = sentence.lower()
    if re.search(r"\b\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?\b", sentence):
        return True
    if re.search(r"\b\d{1,2}(?:st|nd|rd|th)?\s+[a-z]{3,9}\b", low):
        return True
    if re.search(r"\b[a-z]{3,9}\s+\d{1,2}(?:st|nd|rd|th)?\b", low):
        return True
    if any(w in low for w in WEEKDAYS) or "tomorrow" in low or "next week" in low:
        return True
    return False


def parse_date(sentence: str, ref: date) -> date | None:
    """Tool: turn a deadline sentence into an actual date, relative to ref."""
    low = sentence.lower()

    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", sentence)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        y = int(m.group(3)) if m.group(3) else ref.year
        if y < 100:
            y += 2000
        try:
            return date(y, mo, d)
        except ValueError:
            pass

    m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]{3,9})\b", low)
    if not m:
        m = re.search(r"\b([a-z]{3,9})\s+(\d{1,2})(?:st|nd|rd|th)?\b", low)
        if m:
            day_s, mon_s = m.group(2), m.group(1)
        else:
            day_s = mon_s = None
    else:
        day_s, mon_s = m.group(1), m.group(2)
    if day_s and mon_s:
        month = MONTHS.get(mon_s[:3])
        if month:
            y = ref.year if (month, int(day_s)) >= (ref.month, ref.day) else ref.year + 1
            try:
                return date(y, month, int(day_s))
            except ValueError:
                pass

    if "tomorrow" in low:
        return ref + timedelta(days=1)
    if "next week" in low:
        return ref + timedelta(days=7)
    for name, wd in WEEKDAYS.items():
        if name in low:
            delta = (wd - ref.weekday()) % 7
            delta = delta if delta else 7
            return ref + timedelta(days=delta)
    return None


def verify_quote(mail: Mail, quote: str) -> bool:
    """Tool: prove the quoted sentence really is in the mail, verbatim."""
    norm = lambda t: re.sub(r"\s+", " ", t).strip().lower()
    return norm(quote) in norm(mail.body)


def detect_injection(mail: Mail) -> list[str]:
    """Tool: flag prompt-injection style instructions hidden in mail text."""
    findings = []
    for pat in INJECTION_PATTERNS:
        if re.search(pat, mail.body, re.IGNORECASE):
            findings.append(pat)
    return findings


def tag_course(sentence: str, subject: str = "") -> str:
    """Tool: tag a deadline with its course."""
    text = (sentence + " " + subject).lower()
    for course, keys in COURSE_KEYWORDS.items():
        if any(k in text for k in keys):
            return course
    return "General"


def preview_reminder(dl: Deadline) -> dict:
    """Tool: build the reminder the student WOULD get. Nothing is sent."""
    return {
        "channel": "whatsapp (planned, not live)",
        "text": f"Reminder: {dl.what} ({dl.course}) is due on {dl.due.isoformat()}.",
        "status": "preview only - nothing sent",
    }

_PREP_HINTS = {
    "Agentic AI": "rehearse the demo and re-read the paper's results tables",
    "DS": "re-run the lab code and revise the concept notes",
    "OOMD": "redraw the UML diagrams once by hand",
    "Placement": "practise one aptitude set and update the resume printout",
    "General": "read the mail once more and note what to carry",
}


def make_note(dl: "Deadline") -> dict:
    """Tool: write the Noter agent's prep note for one deadline.

    A note is private to the student - it is never sent anywhere.
    """
    days = (dl.due - date.today()).days
    if days < 0:
        priority = "OVERDUE"
    elif days <= 2:
        priority = "high"
    elif days <= 7:
        priority = "medium"
    else:
        priority = "low"
    first_step = _PREP_HINTS.get(dl.course, _PREP_HINTS["General"])
    return {
        "course": dl.course,
        "task": dl.what,
        "due": dl.due.isoformat(),
        "days_left": days,
        "priority": priority,
        "first_step": first_step,
        "evidence": dl.quote,
        "status": "note only - nothing sent",
    }

