"""CampusInbox + LangGraph: the deadline agent rebuilt as a LangGraph state graph with LangChain tool calling.

Same five deterministic mail tools and the same safety gate as the plain-Python agent_loop.py:
the model may only choose which tool to call next; check_quote re-verifies every proposed answer IN CODE,
and a failed gate triggers one reflection turn. The graph:

    START -> agent -> (tools -> agent)* -> verify -> END        (at most MAX_STEPS model turns)

Offline: ScriptedModel (offline_model.py) drives the same graph with no API key and no network.
Online:  pass any LangChain chat model that supports .bind_tools (ChatOpenAI, ChatGoogleGenerativeAI, ...).

This file is an EXTENSION. The paper's numbers came from the plain-Python loop in CampusInbox_MVP/agent_loop.py.
"""
import functools
import json
import sys
from pathlib import Path
from typing import Annotated, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "CampusInbox_MVP"))
import agent_loop as plain  # reuse MailTools and the same SYSTEM prompt

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool

MAX_STEPS = plain.MAX_STEPS


def mail_tools(mt: plain.MailTools):
    """Wrap the same five MailTools methods (plus final_answer) as LangChain StructuredTools."""
    def read_header() -> str:
        """Return the mail's Date header and weekday."""
        return json.dumps(mt.read_header())

    def search_mail(query: str = "") -> str:
        """List up to 8 numbered sentences that hold a deadline cue or a date expression."""
        return json.dumps(mt.search_mail(query))

    def read_context(n: int = 0) -> str:
        """Return sentence n with its neighbours."""
        return json.dumps(mt.read_context(n))

    def parse_date(text: str = "") -> str:
        """Resolve the date expression in a text to an ISO date against the Date header, or null."""
        return json.dumps(mt.parse_date(text))

    def check_quote(quote: str = "", date_iso: str = "") -> str:
        """Check that a quote is verbatim in the mail and holds the date."""
        return json.dumps(mt.check_quote(quote, date_iso))

    def final_answer(has_deadline: bool, deadline_date: str = "", ambiguous: bool = False, quote: str = "") -> str:
        """Finish. Use has_deadline false if no single actionable date exists. Always call check_quote first."""
        return json.dumps({"has_deadline": has_deadline, "deadline_date": deadline_date,
                           "ambiguous": ambiguous, "quote": quote})

    return [StructuredTool.from_function(f) for f in
            (read_header, search_mail, read_context, parse_date, check_quote, final_answer)]


class State(TypedDict):
    messages: Annotated[list, add_messages]
    steps: int
    reflected: bool
    result: dict


def build_graph(model, mt: plain.MailTools):
    tlist = mail_tools(mt)
    bound = model.bind_tools(tlist) if hasattr(model, "bind_tools") else model
    tool_node = ToolNode(tlist)

    def agent(state: State):
        msgs = [SystemMessage(content=plain.SYSTEM),
                HumanMessage(content="Mail subject: " + mt.subject[:200] + "\nFind the deadline using your functions.")]
        msgs += state["messages"]
        ai = bound.invoke(msgs)
        return {"messages": [ai], "steps": state["steps"] + 1}

    def after_agent(state: State):
        ai = state["messages"][-1]
        if getattr(ai, "tool_calls", None) and state["steps"] < MAX_STEPS:
            return "tools"
        return END

    def _last_ai_calls(state: State):
        for m in reversed(state["messages"]):
            if isinstance(m, AIMessage):
                return [c["name"] for c in (m.tool_calls or [])]
        return []

    def after_tools(state: State):
        return "verify" if "final_answer" in _last_ai_calls(state) else "agent"

    def verify(state: State):
        """The safety gate, in code, not in the model: re-check the quote before any answer stands."""
        ai = next(m for m in reversed(state["messages"]) if isinstance(m, AIMessage) and m.tool_calls)
        args = next(c["args"] for c in ai.tool_calls if c["name"] == "final_answer")
        due = args.get("deadline_date") if args.get("has_deadline") else None
        quote = args.get("quote") or ""
        if due:
            chk = mt.check_quote(quote, due)
            if not chk["ok"]:
                if not state["reflected"] and state["steps"] < MAX_STEPS:
                    return {"messages": [HumanMessage(
                        content="The quote check failed: %s. Revise, or finish with has_deadline false." % chk["reason"])],
                        "reflected": True}
                return {"result": {"due": None, "quote": quote, "ambiguous": bool(args.get("ambiguous")),
                                   "note": "gate rejected: " + chk["reason"]}}
        return {"result": {"due": due, "quote": quote, "ambiguous": bool(args.get("ambiguous")), "note": ""}}

    def after_verify(state: State):
        return END if state["result"] else "agent"

    g = StateGraph(State)
    g.add_node("agent", agent)
    g.add_node("tools", tool_node)
    g.add_node("verify", verify)
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", after_agent, {"tools": "tools", END: END})
    g.add_conditional_edges("tools", after_tools, {"agent": "agent", "verify": "verify"})
    g.add_conditional_edges("verify", after_verify, {"agent": "agent", END: END})
    return g.compile()


def trace_of(messages):
    out = []
    for m in messages:
        if isinstance(m, AIMessage) and m.tool_calls:
            for c in m.tool_calls:
                out.append({"tool": c["name"], "args": c["args"]})
        elif isinstance(m, ToolMessage):
            out.append({"observation": str(m.content)[:400]})
    return out


def run_langgraph_agent(model, subject, body, ref):
    """Same interface as agent_loop.run_agent. model: any LangChain chat model or ScriptedModel."""
    mt = plain.MailTools(subject, body, ref)
    final = build_graph(model, mt).invoke({"messages": [], "steps": 0, "reflected": False, "result": {}})
    res = final.get("result") or {"due": None, "quote": "", "ambiguous": False, "note": "step limit"}
    res["trace"] = trace_of(final["messages"])
    res["engine"] = "langgraph"
    return res
