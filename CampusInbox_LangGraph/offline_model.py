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
            self._hits = hits
            self._hit_i = 0
            self._quote = hits[0]["sentence"]
            return self._call(3, "parse_date", {"text": hits[0]["sentence"]})
        if n >= 3 and isinstance(last, dict) and "ok" in last:
            # check_quote result
            if not last.get("ok"):
                return self._call(n + 1, "final_answer", {"has_deadline": False, "ambiguous": False})
            return self._call(n + 1, "final_answer", {"has_deadline": True, "deadline_date": self._due, "quote": self._quote})
        if n >= 3 and isinstance(last, dict) and "date" in last:
            # parse_date result
            if last.get("date"):
                self._due = last["date"]
                return self._call(n + 1, "check_quote", {"quote": self._quote, "date_iso": self._due})
            # One reflection-style retry per remaining deadline-cue sentence, then abstain.
            self._hit_i = getattr(self, "_hit_i", 0) + 1
            hits = getattr(self, "_hits", [])
            if self._hit_i < len(hits):
                self._quote = hits[self._hit_i]["sentence"]
                return self._call(n + 1, "parse_date", {"text": hits[self._hit_i]["sentence"]})
            return self._call(n + 1, "final_answer", {"has_deadline": False, "ambiguous": True})
        # After a reflection turn: finish safely rather than loop.
        return self._call(n + 1, "final_answer", {"has_deadline": False, "ambiguous": True})
