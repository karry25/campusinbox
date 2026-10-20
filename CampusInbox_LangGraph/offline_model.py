"""ScriptedModel: a deterministic, offline stand-in for an LLM, for tests and demos with no API key.

It speaks the LangChain chat-model interface (bind_tools + invoke -> AIMessage with tool_calls) and follows
the same fixed tool policy as the plain loop's offline fallback (agent_loop.run_scripted). It proves the
LangGraph machinery (nodes, edges, ToolNode, gate, reflection) works; swap in a real model for live use.
"""
import json
from langchain_core.messages import AIMessage, ToolMessage


class ScriptedModel:
    def __init__(self):
        self._quote = ""
        self._due = ""

    def bind_tools(self, tlist):
        return self

    def _call(self, n, name, args):
        return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": "call_%d" % n, "type": "tool_call"}])

    def invoke(self, messages):
        tool_msgs = [m for m in messages if isinstance(m, ToolMessage)]
        n = len(tool_msgs)
        last = None
        if tool_msgs:
            try:
                last = json.loads(tool_msgs[-1].content)
            except (TypeError, ValueError):
                last = None
        if n == 0:
            return self._call(1, "read_header", {})
        if n == 1:
            return self._call(2, "search_mail", {})
        if n == 2:
            hits = [h for h in (last or []) if h.get("deadline_cue")] if isinstance(last, list) else []
            if not hits:
                return self._call(3, "final_answer", {"has_deadline": False, "ambiguous": False})
            self._quote = hits[0]["sentence"]
            return self._call(3, "parse_date", {"text": hits[0]["sentence"]})
        if n == 3:
            if not (last or {}).get("date"):
                return self._call(4, "final_answer", {"has_deadline": False, "ambiguous": True})
            self._due = last["date"]
            return self._call(4, "check_quote", {"quote": self._quote, "date_iso": self._due})
        if n == 4:
            if not (last or {}).get("ok"):
                return self._call(5, "final_answer", {"has_deadline": False, "ambiguous": False})
            return self._call(5, "final_answer", {"has_deadline": True, "deadline_date": self._due, "quote": self._quote})
        # After a reflection turn: finish safely rather than loop.
        return self._call(n + 1, "final_answer", {"has_deadline": False, "ambiguous": True})
