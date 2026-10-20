"""Offline tests for the LangGraph extension. Run: python3 test_langgraph.py"""
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "CampusInbox_MVP"))

import agent_loop as plain
import campus_tools as ct
from langgraph_agent import run_langgraph_agent
from offline_model import ScriptedModel

REF = date(2026, 10, 21)  # a Wednesday
passed = failed = 0


def check(name, cond, extra=""):
    global passed, failed
    if cond:
        passed += 1
        print("PASS", name)
    else:
        failed += 1
        print("FAIL", name, extra)


MAILS = [
    ("lab", "Agentic AI lab submission", "Upload the report and source code. Due: 2026-10-24. Submission status is not included.", "2026-10-24"),
    ("friday", "Agentic AI: FA2 paper presentation slides", "Dear students, the FA2 paper presentation slides must be submitted by Friday. Late submissions lose 20 percent.", "2026-10-23"),
    ("info-only", "Library workshop", "A Zotero workshop will be held on October 28 in the library. All are welcome.", None),
    ("ambiguous", "Project", "Submit next Friday. Late submissions lose marks.", None),
]

# 1) LangGraph engine agrees with the plain-Python offline loop on the same mails
for name, subj, body, want in MAILS:
    got = run_langgraph_agent(ScriptedModel(), subj, body, REF)
    ref = plain.run_scripted(subj, body, REF)
    check("langgraph due == plain due [%s]" % name, got["due"] == ref["due"] == want,
          "got=%r plain=%r want=%r" % (got["due"], ref["due"], want))
    check("trace shows real tool calls [%s]" % name, any(t.get("tool") == "search_mail" for t in got["trace"]))

# 2) the gate still rejects a bad quote (safety): a mail whose 'deadline' quote is not verbatim must not pass
mt = plain.MailTools("s", "Submit the form by October 30.", REF)
check("gate rejects wrong date", not mt.check_quote("Submit the form by October 30.", "2026-10-31")["ok"])
check("gate rejects invented quote", not mt.check_quote("Submit the form by October 29.", "2026-10-29")["ok"])

# 3) date calculator
dc = ct.make_date_calculator(today=REF)
check("friday resolves", json.loads(dc.invoke({"text": "submitted by Friday"}))["date"] == "2026-10-23")
check("days left", json.loads(dc.invoke({"text": "submitted by Friday"}))["days_left"] == 2)
check("next Friday stays ambiguous", json.loads(dc.invoke({"text": "next Friday"}))["date"] is None)

# 4) gmail demo tool is read-only over the synthetic inbox
gs = json.loads(ct.make_gmail_search("demo").invoke({"query": ""}))
check("demo inbox lists mails", len(gs) >= 5 and all("subject" in m for m in gs))

# 5) calendar: read-only list + proposal-only event (no write function exists)
check("calendar demo events", len(json.loads(ct.make_calendar_events("demo").invoke({"days_ahead": 7}))["events"]) >= 1)
prop = json.loads(ct.make_calendar_propose("demo").invoke({"title": "RM paper due", "date_iso": "2026-10-23"}))
check("calendar proposal only", prop["status"].startswith("proposal only") and prop["add_it_yourself_link"].startswith("https://calendar.google.com/calendar/render?"))
import google_calendar
check("no calendar write function exists", not hasattr(google_calendar, "create_event") and not hasattr(google_calendar, "insert_event"))

# 6) web search demo is clearly labelled and real mode is off without env
ws = json.loads(ct.make_web_search("demo").invoke({"query": "x"}))
check("web demo labelled", "demo" in ws["mode"])

# 7) demo_mode runs end to end non-interactively and is clearly labelled
r = subprocess.run([sys.executable, "demo_mode.py", "--auto"], capture_output=True, text=True, cwd=Path(__file__).parent)
t = r.stdout
check("demo runs clean", r.returncode == 0, r.stderr[-400:])
check("demo labelled not-real", "NOT a real Google login" in t and "DEMO MODE" in t)
check("demo finds friday deadline", "DEADLINE FOUND: 2026-10-23" in t or "DEADLINE FOUND" in t)
check("demo shows time left", "day(s) left" in t)
check("demo proposal-only", "proposal only" in t)
check("transcript saved", (Path(__file__).parent / "demo_transcript.txt").exists())


# 8) reminder preview never sends and shows the exact text
from reminder_preview import make_reminder_tool, PREVIEW
rem = json.loads(make_reminder_tool().invoke({"title": "RM paper", "date_iso": "2026-10-23", "human_time_left": "2 day(s) left"}))
check("reminder preview only", rem["status"] == PREVIEW and "2026-10-23" in rem["whatsapp_preview"]["payload"]["text"]["body"])
check("reminder has email preview", rem["email_preview"]["subject"] == "CampusInbox reminder")

# 9) planner graph: whole pipeline over the demo inbox
from planner_graph import build_planner
plan = build_planner(today=date(2026, 10, 21)).invoke({"mails": [], "findings": [], "report": ""})
friday = [f for f in plan["findings"] if f["id"] == "demo-agentic"]
check("planner finds friday deadline", friday and friday[0]["due"] == "2026-10-23", str(friday))
check("planner report mentions reminder preview", "reminder preview" in plan["report"])

# 10) chatbot over demo inbox cites sources
import chatbot
corpus = chatbot.Corpus(ct.demo_inbox(ct.DEMO_EXTRA_MAILS))
a = chatbot.answer_offline(corpus, "When are the FA2 slides due?")
check("chat answers with citation", bool(a["citations"]) and "demo-agentic" in a["citations"][0]["id"])

# 11) course tagging + per-subject view
check("explicit course field wins", ct.tag_course({"subject": "x", "body": "y", "course": "OOMD"}) == "OOMD")
check("keyword course tag", ct.tag_course({"subject": "DS report deadline revised", "body": "portal"}) == "Distributed Systems")
check("untagged mail is Other", ct.tag_course({"subject": "Canteen menu", "body": "paneer today"}) == "Other")
grp = ct.group_by_course([{"subject": "OOMD term-work file", "due": "2026-10-30"},
                          {"subject": "Agentic AI slides", "due": "2026-10-23"}])
check("group by course", set(grp) == {"OOMD", "Agentic AI"} and grp["OOMD"][0]["due"] == "2026-10-30")
plan2 = build_planner(today=date(2026, 10, 21)).invoke({"mails": [], "findings": [], "report": ""})
check("planner report groups by course", "[Agentic AI]" in plan2["report"] and "[Placement cell]" in plan2["report"])
check("planner finds placement deadline", any(f.get("due") == "2026-10-28" and f["course"] == "Placement cell" for f in plan2["findings"]), str([(f['id'], f.get('due')) for f in plan2['findings']]))

print("\n%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
