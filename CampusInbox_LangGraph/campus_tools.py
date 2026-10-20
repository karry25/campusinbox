"""Extended LangChain tools for CampusInbox: date math, Gmail (read-only), Google Calendar (read-only +
proposal-only events) and optional web search. Each tool is a factory so demos can inject mock backends
and tests can run fully offline. Real Google access stays user-run on the student's own laptop."""
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "CampusInbox_MVP"))
import rules_v2
from langchain_core.tools import StructuredTool


# ---------- date calculator ----------

def make_date_calculator(today=None):
    """'Friday deadline' -> real date + time left. today is injectable for tests/demos."""
    today = today or date.today()

    def date_calculator(text: str) -> str:
        """Resolve a date expression like 'Friday' or 'Oct 24' to a real date and the time left from today."""
        found = rules_v2.dates_in(text, today)
        if not found:
            return json.dumps({"date": None, "reason": "no date expression in: " + text[:120]})
        if any(k == "amb" or d is None for d, _, k in found):
            return json.dumps({"date": None, "reason": "ambiguous date expression", "matched": [t for _, t, _ in found]})
        uniq = sorted({d for d, _, _ in found})
        if len(uniq) > 1:
            return json.dumps({"date": None, "reason": "several different dates", "dates": [d.isoformat() for d in uniq]})
        d = uniq[0]
        delta = d - today
        return json.dumps({"date": d.isoformat(), "weekday": d.strftime("%A"), "today": today.isoformat(),
                           "days_left": delta.days, "hours_left": delta.days * 24,
                           "human": ("%s, %s - %d day(s) left" % (d.strftime("%A"), d.isoformat(), delta.days))
                           if delta.days >= 0 else ("%s, %s - %d day(s) AGO" % (d.strftime("%A"), d.isoformat(), -delta.days))})
    return StructuredTool.from_function(date_calculator)


# ---------- Gmail (read-only) ----------

def demo_inbox(extra=None):
    """The DEMO inbox: the project's synthetic sample mails plus demo extras. No real account involved."""
    mails = json.loads((Path(__file__).resolve().parent.parent / "CampusInbox_MVP" / "sample_mails.json").read_text())
    for m in mails:
        m.setdefault("date", date.today().isoformat())
    return mails + (extra or [])


def make_gmail_search(provider="demo", max_n=10):
    """gmail_search lists recent mails (id, subject, date). provider='demo' reads the synthetic inbox;
    provider='real' uses gmail_auth.fetch_recent (needs the student's own OAuth sign-in on her laptop)."""
    def gmail_search(query: str = "") -> str:
        """List recent mails in the inbox, optionally filtered by a word. Read-only."""
        if provider == "demo":
            mails = demo_inbox(DEMO_EXTRA_MAILS)
        else:
            import gmail_auth
            try:
                mails = gmail_auth.fetch_recent(max_n=max_n)
            except FileNotFoundError:
                return json.dumps({"error": "not signed in. Run the Gmail sign-in on your own laptop first (see README)."})
            except Exception as e:
                return json.dumps({"error": "gmail read failed: " + type(e).__name__})
        if query:
            mails = [m for m in mails if query.lower() in (m.get("subject", "") + m.get("body", "")).lower()]
        return json.dumps([{"id": m["id"], "subject": m["subject"][:80], "date": m.get("date", "")} for m in mails[:max_n]])
    return StructuredTool.from_function(gmail_search)


# ---------- Google Calendar (read-only + proposal-only writes) ----------

DEMO_CALENDAR = [
    {"summary": "Agentic AI lecture", "start": "2026-10-21T10:00:00+05:30", "end": "2026-10-21T11:00:00+05:30"},
    {"summary": "DS lab", "start": "2026-10-22T14:00:00+05:30", "end": "2026-10-22T16:00:00+05:30"},
]

# The multi-course demo scenario: synthetic mails from four courses plus one info mail.
# Every body is labelled synthetic. Dates are written so they resolve against "today" at demo time.
DEMO_EXTRA_MAILS = [
    {"id": "demo-agentic", "course": "Agentic AI", "subject": "Agentic AI: FA2 paper presentation slides",
     "body": "SAMPLE MAIL - synthetic, not a real college message.\nDear students, the FA2 paper presentation slides must be submitted by Friday. Late submissions lose 20 percent.",
     "date": date.today().isoformat()},
    {"id": "demo-ds", "course": "Distributed Systems", "subject": "DS report deadline revised",
     "body": "SAMPLE MAIL - synthetic, not a real college message.\nThe report deadline is revised: 24 October. Please upload the PDF on the portal.",
     "date": date.today().isoformat()},
    {"id": "demo-oomd", "course": "OOMD", "subject": "OOMD term-work file",
     "body": "SAMPLE MAIL - synthetic, not a real college message.\nThe term-work file submission closes on 30 October. No extensions will be given.",
     "date": date.today().isoformat()},
    {"id": "demo-placement", "course": "Placement cell", "subject": "Upload certificates",
     "body": "SAMPLE MAIL - synthetic, not a real college message.\nAll shortlisted students must upload certificates by the 28th on the placement portal.",
     "date": date.today().isoformat()},
    {"id": "demo-info", "course": "Other", "subject": "Library workshop",
     "body": "SAMPLE MAIL - synthetic, not a real college message.\nA Zotero workshop will be held on October 28 in the library. All are welcome.",
     "date": date.today().isoformat()},
]

COURSE_RULES = [
    ("Agentic AI", ("agentic",)),
    ("Distributed Systems", ("distributed systems", "ds report", "ds lab")),
    ("OOMD", ("oomd", "modelling and design", "term-work")),
    ("Research Methodology", ("research methodolog", "rm paper")),
    ("Placement cell", ("placement", "certificate")),
]


def tag_course(mail):
    """A mail's course: an explicit 'course' field wins; otherwise simple keyword rules over
    subject+body. Returns 'Other' when nothing matches. Honest heuristic, not a classifier."""
    if mail.get("course"):
        return mail["course"]
    text = (mail.get("subject", "") + "\n" + mail.get("body", "")).lower()
    for name, keys in COURSE_RULES:
        if any(k in text for k in keys):
            return name
    return "Other"


def group_by_course(items):
    """items: dicts with a 'mail' or 'subject' key (and any deadline fields). Returns
    {course: [items]}, the per-subject deadline view used by the planner and demo."""
    out = {}
    for it in items:
        mail = it.get("mail") or {"subject": it.get("subject", ""), "body": it.get("body", "")}
        out.setdefault(tag_course(mail), []).append(it)
    return dict(sorted(out.items()))


def make_calendar_events(provider="demo"):
    def calendar_events(days_ahead: int = 7) -> str:
        """List calendar events for the next days_ahead days, to check free time around a deadline. Read-only."""
        if provider == "demo":
            return json.dumps({"mode": "demo", "events": DEMO_CALENDAR})
        import google_calendar
        try:
            return json.dumps({"mode": "real", "events": google_calendar.list_events(days=days_ahead)})
        except FileNotFoundError:
            return json.dumps({"error": "not signed in. Run the Calendar sign-in on your own laptop first (see README)."})
        except Exception as e:
            return json.dumps({"error": "calendar read failed: " + type(e).__name__})
    return StructuredTool.from_function(calendar_events)


def make_calendar_propose(provider="demo"):
    def calendar_propose_event(title: str, date_iso: str) -> str:
        """Prepare a calendar event for a deadline. PROPOSAL ONLY: nothing is written by the app. The student
        reviews the proposal and adds it herself with the returned link."""
        import google_calendar
        link = google_calendar.propose_link(title, date_iso, details="Proposed by CampusInbox. Review before saving.")
        return json.dumps({"status": "proposal only - nothing was added to your calendar",
                           "title": title, "date": date_iso,
                           "add_it_yourself_link": link,
                           "note": "The app cannot write to your calendar. Open the link and press Save if you agree."})
    return StructuredTool.from_function(calendar_propose_event)


# ---------- web search (optional, off by default) ----------

def make_web_search(provider="demo"):
    def web_search(query: str) -> str:
        """Search the web, e.g. for a conference deadline. Off unless enabled; demo returns fixed sample results."""
        if provider == "demo":
            return json.dumps({"mode": "demo (sample results, not live)",
                               "results": [{"title": "Example Conference 2027 - Call for Papers",
                                            "url": "https://example.org/cfp",
                                            "snippet": "Sample result for the demo video. Live search needs CAMPUS_WEB=1 and CAMPUS_SEARCH_URL."}]})
        import chatbot
        if not chatbot.web_enabled():
            return json.dumps({"error": "web search is off. Set CAMPUS_WEB=1 and CAMPUS_SEARCH_URL (see README)."})
        try:
            return json.dumps(chatbot.search_live(query))
        except Exception as e:
            return json.dumps({"error": "web search failed: " + type(e).__name__})
    return StructuredTool.from_function(web_search)
