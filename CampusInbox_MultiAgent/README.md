# CampusInbox - Multi-Agent Version (extension)

A multi-agent rebuild of the CampusInbox deadline extractor. **This is a separate
package - the original tested single-agent MVP and its LangGraph extension are
untouched, and the published accuracy numbers (98.3% test split, silver labels)
still belong to that version, not this one.**

## The agents

| Agent | Job | Tools it calls |
|---|---|---|
| Reader | reads each mail: date header + candidate deadline sentences | `read_date_header`, `find_deadline_sentences` |
| Extractor | turns a sentence into a structured deadline: real date + course tag | `parse_date`, `tag_course` |
| Verifier | blocks anything unproven or hostile | `verify_quote` (verbatim proof), `detect_injection` |
| Planner | groups by course and previews reminders | `preview_reminder` (nothing is ever sent) |
| Noter | writes a prep note per deadline: priority, days left, first step | `make_note` (notes only, never sent) |
| Coordinator | routes work between agents, keeps the trace log | - |
| Human gate | approves/rejects each proposed deadline | the student |

## The chatbot (tool calling + web calls)

`ChatbotAgent` answers questions through an **explicit ReAct loop**: every
answer shows its `Thought -> Action -> Observation` trace before the final
answer. Its tools: listing deadlines, per-course views, "what's next", date
parsing, **vector-store retrieval over the imported mails** (`search_mails` -
a small stdlib vector database: sentences embedded as TF-IDF vectors, cosine
nearest-neighbour search, answers cite the source mail and score), and **live
web search** (DuckDuckGo; if the network is unavailable it falls back to a
small demo index and says `mode: demo-fallback` in the answer, so nobody
mistakes it for live).

Honesty note: in demo mode (no LLM API key) the *Thought* steps and tool
selection come from a deterministic rule-based planner, not a language model.
The tools, the vector store and the web calls are real. Wiring a model to
produce the thoughts is the API-key extension.

## Run (Python 3.10+, stdlib only)

```
python -m campusinbox_ma.demo            # full pipeline + human approval
python -m campusinbox_ma.demo --auto     # skip approval (deadlines stay "waiting")
python -m campusinbox_ma.demo --chat     # then talk to the chatbot
python -m unittest discover -s tests     # 26 tests
```

Windows: double-click `start_windows.bat`.

## Demo mode - say this in viva

Sample mails are local files, sign-in is simulated, reminders are previews and
nothing is sent. One sample mail contains a hidden prompt-injection note on
purpose: the Verifier agent blocks it, which demos the safety check. Live Gmail,
WhatsApp sending and LLM-based tool selection are built-for / future scope, not
live-tested.
