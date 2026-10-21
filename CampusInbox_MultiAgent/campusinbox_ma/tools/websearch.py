"""Web search tool for the chatbot agent.

Tries a live DuckDuckGo HTML query first. If the network or the endpoint is
unavailable, it falls back to a small built-in demo index and SAYS SO in the
result. Live mode is best-effort and not part of the tested numbers.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

_DEMO_INDEX = {
    "langgraph": [
        {"title": "LangGraph docs (demo entry)", "url": "https://langchain-ai.github.io/langgraph/",
         "snippet": "Build agents as graphs: nodes are steps, edges are what runs next."},
    ],
    "pccoe": [
        {"title": "PCCOE Pune (demo entry)", "url": "https://www.pccoepune.com/",
         "snippet": "Pimpri Chinchwad College of Engineering, Pune."},
    ],
    "prompt injection": [
        {"title": "OWASP LLM Top 10 (demo entry)", "url": "https://owasp.org/www-project-top-10-for-large-language-model-applications/",
         "snippet": "Prompt injection is LLM01: untrusted text tries to steer the agent."},
    ],
}


def web_search(query: str, live: bool = True, timeout: int = 6) -> dict:
    """Tool: search the web. Returns {mode, results:[{title,url,snippet}]}.

    mode is 'live' when results really came from the network and
    'demo-fallback' when they came from the built-in index. Callers must show
    the mode so nobody mistakes demo results for live ones.
    """
    if live:
        try:
            return {"mode": "live", "results": _duckduckgo(query, timeout)}
        except Exception:
            pass  # fall through to demo, labelled
    results = []
    low = query.lower()
    for key, items in _DEMO_INDEX.items():
        if key in low:
            results.extend(items)
    if not results:
        results = [{"title": f"No demo result for '{query}'",
                    "url": "", "snippet": "Demo index only covers a few topics; live search was unavailable."}]
    return {"mode": "demo-fallback", "results": results}


def _duckduckgo(query: str, timeout: int) -> list[dict]:
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")
    out = []
    for m in re.finditer(
        r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.S
    ):
        link = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        href = m.group(1)
        out.append({"title": link, "url": href, "snippet": ""})
        if len(out) >= 5:
            break
    if not out:
        raise RuntimeError("no results parsed")
    return out
