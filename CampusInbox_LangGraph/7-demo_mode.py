"""CampusInbox DEMO MODE - a clearly labelled fake sign-in over a synthetic sample inbox, for the demo video.

THIS IS NOT A REAL GOOGLE SIGN-IN. It uses the project's synthetic sample mails and mock calendar/reminder
backends so the FULL agent flow can be shown on any machine with no account, no keys and no network:
  simulated sign-in -> inbox -> LangGraph agent with tool calling per mail -> deadline + time left ->
  calendar free-check + proposal -> reminder preview -> chat over the inbox.
The real Google sign-in path stays separate (see README). The paper's privacy claim ("no real student mail
goes to a model API") is untouched: this demo runs the offline scripted model.

Run:  python3 demo_mode.py          (interactive; screen-record the terminal for the demo video)
      python3 demo_mode.py --auto   (non-interactive, for tests)
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "CampusInbox_MVP"))

import campus_tools as ct
import chatbot
from langgraph_agent import run_langgraph_agent
from offline_model import ScriptedModel
from reminder_preview import make_reminder_tool, PREVIEW

LOG = []


def out(s=""):
    print(s)
    LOG.append(s)


def ask(prompt, auto_answer=""):
    if "--auto" in sys.argv:
        out(prompt + " " + auto_answer)
        return auto_answer
    r = input(prompt + " ")
    LOG.append(prompt + " " + r)
    return r.strip()


def main():
    out("=" * 66)
    out("  CampusInbox  -  DEMO MODE  (sample student inbox)")
    out("  This is a simulated sign-in for the demo video.")
    out("  NOT a real Google login. No real account or mail is used.")
    out("=" * 66)
    out()
    out("[demo] Sign in with Google (SIMULATED)")
    email = ask("[demo] Email [demo.student@campusinbox.example]:", "") or "demo.student@campusinbox.example"
    ask("[demo] Password [hidden, not checked - demo only]:", "********")
    out("[demo] Signed in as %s (DEMO ACCOUNT - synthetic inbox)" % email)
    out()

    mails = ct.demo_inbox(ct.DEMO_EXTRA_MAILS)
    out("[demo] Inbox: %d mails found" % len(mails))
    for m in mails:
        out("   - %-42s %-20s %s" % (m["subject"][:42], "[" + ct.tag_course(m) + "]", m.get("date", "")))
    out()

    calc = ct.make_date_calculator(today=date.today())
    cal_events = ct.make_calendar_events("demo")
    cal_propose = ct.make_calendar_propose("demo")
    remind = make_reminder_tool(today=date.today())

    for m in mails:
        out("-" * 66)
        out("MAIL: %s" % m["subject"])
        res = run_langgraph_agent(ScriptedModel(), m["subject"], m["body"], date.today())
        out("  LangGraph agent trace (each AI line is one tool call):")
        for t in res["trace"]:
            if "tool" in t:
                out("    AI -> tool %-14s %s" % (t["tool"], json.dumps(t["args"])[:70]))
            else:
                out("    tool result: %s" % t["observation"][:110])
        if res["due"]:
            out("  DEADLINE FOUND: %s" % res["due"])
            out("  evidence quote: \"%s\"" % res["quote"][:90])
            info = json.loads(calc.invoke({"text": res["quote"]}))
            out("  date calculator: %s" % info.get("human", info.get("reason")))
            ev = json.loads(cal_events.invoke({"days_ahead": 7}))
            out("  calendar (next 7 days, read-only): %s" % (", ".join(e["summary"] for e in ev["events"]) or "free"))
            prop = json.loads(cal_propose.invoke({"title": "DUE: " + m["subject"][:50], "date_iso": res["due"]}))
            out("  calendar proposal: \"%s\" on %s - %s" % (prop["title"], prop["date"], prop["status"]))
            ans = ask("  Add it yourself via the link? (y/n)", "y")
            if ans.lower().startswith("y"):
                out("  " + prop["add_it_yourself_link"])
            rem = json.loads(remind.invoke({"title": m["subject"], "date_iso": res["due"],
                                            "human_time_left": info.get("human", "")}))
            out("  reminder the agent WOULD send (preview, not sent):")
            out("    WhatsApp: " + rem["whatsapp_preview"]["payload"]["text"]["body"])
            out("    Email:    Subject: %s | %s" % (rem["email_preview"]["subject"], rem["email_preview"]["body"]))
            out("  note: " + PREVIEW)
        else:
            out("  No single actionable deadline (%s)." % (res["note"] or ("ambiguous" if res["ambiguous"] else "none found")))
    out()
    out("-" * 66)
    out("DEADLINES BY COURSE (per-subject view):")
    found = []
    for m in mails:
        r = run_langgraph_agent(ScriptedModel(), m["subject"], m["body"], date.today())
        if r["due"]:
            found.append({"subject": m["subject"], "body": m["body"], "due": r["due"]})
    for course, items in ct.group_by_course(found).items():
        out("  [%s]" % course)
        for it in items:
            out("    - %-40s %s" % (it["subject"][:40], it["due"]))
    out()
    out("-" * 66)
    out("CHAT over the demo inbox (offline retrieval, answers cite the source line):")
    corpus = chatbot.Corpus(mails)
    for q in (["When is the RM paper due?", "What is the lab task?"] if "--auto" in sys.argv else [ask("  Ask a question about the mails:", "When is the RM paper due?")]):
        if not q:
            continue
        a = chatbot.answer_offline(corpus, q)
        out("  Q: %s" % q)
        out("  A: %s" % a["answer"][:200])
        for c in a["citations"]:
            out("     source: %s" % c["source"])
    out()
    out("=" * 66)
    out("  END OF DEMO. Everything above used the synthetic inbox and the")
    out("  offline scripted model. No real account, mail, calendar or phone")
    out("  was touched; no message was sent; no calendar event was written.")
    out("=" * 66)
    Path("demo_transcript.txt").write_text("\n".join(LOG))
    print("\nTranscript saved to demo_transcript.txt")


if __name__ == "__main__":
    main()
