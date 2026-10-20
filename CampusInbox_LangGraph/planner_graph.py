"""Planner graph: a LangGraph workflow that runs the whole CampusInbox pipeline over an inbox.

Nodes: fetch_mails (gmail_search tool) -> extract (the deadline sub-graph from langgraph_agent per mail)
-> plan (date_calculator + calendar_events + calendar_propose_event + propose_reminder tools) -> report.

The extract node is itself a LangGraph agent with model tool calling; the other nodes call deterministic
tools in code. Offline by default (demo inbox, ScriptedModel); the same graph takes real providers.
"""
import json
import sys
from datetime import date
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "CampusInbox_MVP"))

import campus_tools as ct
from langgraph.graph import StateGraph, START, END
from langgraph_agent import run_langgraph_agent
from offline_model import ScriptedModel
from reminder_preview import make_reminder_tool


class Plan(TypedDict):
    mails: list
    findings: list
    report: str


def build_planner(provider="demo", model_factory=ScriptedModel, today=None):
    today = today or date.today()
    gmail = ct.make_gmail_search(provider)
    calc = ct.make_date_calculator(today=today)
    events = ct.make_calendar_events(provider)
    propose = ct.make_calendar_propose(provider)
    remind = make_reminder_tool(today=today)

    def fetch_mails(state: Plan):
        mails = json.loads(gmail.invoke({"query": ""}))
        full = {m["id"]: m for m in (ct.demo_inbox(ct.DEMO_EXTRA_MAILS) if provider == "demo" else [])}
        return {"mails": [full.get(m["id"], m) for m in mails]}

    def extract(state: Plan):
        findings = []
        for m in state["mails"]:
            res = run_langgraph_agent(model_factory(), m["subject"], m.get("body", ""), today)
            findings.append({"id": m["id"], "subject": m["subject"], "course": ct.tag_course(m),
                             **{k: res[k] for k in ("due", "quote", "ambiguous", "note")}})
        return {"findings": findings}

    def plan(state: Plan):
        out = []
        busy = json.loads(events.invoke({"days_ahead": 7}))["events"]
        for f in state["findings"]:
            if not f["due"]:
                continue
            left = json.loads(calc.invoke({"text": f["quote"] or f["due"]}))
            prop = json.loads(propose.invoke({"title": "DUE: " + f["subject"][:50], "date_iso": f["due"]}))
            rem = json.loads(remind.invoke({"title": f["subject"], "date_iso": f["due"],
                                            "human_time_left": left.get("human", "")}))
            out.append({**f, "time_left": left.get("human", left.get("reason")),
                        "calendar_free_check": [e["summary"] for e in busy],
                        "calendar_proposal": prop, "reminder_preview": rem["console_preview"]})
        lines = ["CampusInbox plan (%d mail(s), %d deadline(s)):" % (len(state["findings"]), len(out))]
        for course, items in ct.group_by_course(out).items():   # per-subject deadline view
            lines.append("[%s]" % course)
            for o in items:
                lines.append("- %s -> %s | %s" % (o["subject"][:50], o["due"], o["time_left"]))
                lines.append("  reminder preview: " + o["reminder_preview"])
        return {"report": "\n".join(lines), "findings": state["findings"]}

    g = StateGraph(Plan)
    g.add_node("fetch_mails", fetch_mails)
    g.add_node("extract", extract)
    g.add_node("plan", plan)
    g.add_edge(START, "fetch_mails")
    g.add_edge("fetch_mails", "extract")
    g.add_edge("extract", "plan")
    g.add_edge("plan", END)
    return g.compile()


if __name__ == "__main__":
    print(build_planner().invoke({"mails": [], "findings": [], "report": ""})["report"])
