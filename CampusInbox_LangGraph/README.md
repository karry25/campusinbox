# CampusInbox - LangGraph extension

An extension folder. The final paper version in `CampusInbox_MVP/` is untouched, and every result in the
paper still comes from the plain-Python loop. This folder adds what the syllabus asks for: the same agent
rebuilt on **LangGraph with LangChain tool calling**, plus Gmail, Google Calendar, web, date-math and
reminder tools, and a demo mode you can screen-record.

## What is here

| file | what it does |
|---|---|
| `langgraph_agent.py` | The deadline agent as a LangGraph state graph: `agent -> (tools -> agent)* -> verify`. Same five mail tools, same `check_quote` safety gate, one reflection turn, 6-turn cap. |
| `offline_model.py` | `ScriptedModel`: an offline stand-in for the LLM (LangChain interface, fixed tool policy). Lets the whole graph run with no API key. Swap in any real LangChain chat model for live use. |
| `campus_tools.py` | Extra tools: `date_calculator` ("by Friday" -> real date + time left), `gmail_search` (read-only), `calendar_events` (read-only), `calendar_propose_event` (proposal only), `web_search` (off by default). |
| `google_calendar.py` | Read-only Google Calendar OAuth (`calendar.readonly`). No event-write function exists anywhere. |
| `reminder_preview.py` | Shows the exact WhatsApp/email reminder the agent would send. Never sends. |
| `planner_graph.py` | A second LangGraph workflow: fetch mails -> extract deadlines (the sub-graph above) -> plan (time left, calendar, reminder preview) -> report. |
| `demo_mode.py` | Simulated sign-in over a synthetic inbox for the demo video. Clearly labelled, no real account. |
| `test_langgraph.py` | 29 offline tests. Run: `python3 test_langgraph.py` |

Setup: `pip install -r requirements.txt` (adds `langgraph` and `langchain-core`; everything else is the
Python standard library, same as the MVP).

## Viva answers (the honest version)

**"Does it use LangChain/LangGraph and tool calling?"**
Yes. The agent is a LangGraph state graph. The nodes are steps (call the model, run a tool, verify the
answer), the edges are the control flow (loop back, retry once, stop). Tools are LangChain
`StructuredTool`s; the model picks the next tool, and the `ToolNode` runs it. We show two engines: the
plain-Python loop (the paper's results) and this LangGraph version (same tools, same gate, same answers).

**"Why also keep the plain Python version?"**
The agent is small, so a hand-written loop gave full control over the evidence checks and made offline
testing easy. LangGraph gives the same behaviour with standard, reusable structure. Keeping both shows the
design trade-off, and the paper lists the framework comparison as future work.

**"Which tools can it call?"**
Mail tools: `read_header`, `search_mail`, `read_context`, `parse_date`, `check_quote`. Planning tools:
`date_calculator`, `gmail_search`, `calendar_events`, `calendar_propose_event`, `propose_reminder`, and an
optional `web_search`. Every answer with a date must pass `check_quote` in code before it stands.

**"Friday deadline - how does it compute the time?"**
`parse_date` resolves "by Friday" against the mail's Date header (a mail dated Wednesday Oct 21 gives
Friday Oct 23). `date_calculator` then returns the weekday and the days/hours left from today. "Next
Friday" stays ambiguous on purpose - the agent abstains instead of guessing.

**"Does it write to my calendar or send messages?"**
No. Calendar events are proposals: the tool returns an "add to Google Calendar" link and the student clicks
Save herself. Reminders are previews: the exact WhatsApp/email text is shown, nothing is sent. Live sending
is implemented in the app but stays off without the student's own credentials, and is not live-tested.

**"Does real student mail go to a model API?"**
No. The Gmail path is read-only and imports through the same human review gate; the offline mode needs no
model at all. The paper's privacy claim still holds.

## Demo video (no account needed)

```
pip install -r requirements.txt
python3 demo_mode.py
```

Screen-record the terminal. The sign-in is simulated over the synthetic inbox and is labelled as such in
every run - say out loud that it is demo mode. The demo shows: inbox, per-mail tool-call trace, deadline +
time left, calendar free-check + proposal link, reminder preview, and chat with cited sources.

## Real Google sign-in (your laptop, optional)

Read-only, standard-library OAuth, token stored in `~/.campusinbox/` with mode 0600. Nothing is shipped.

1. Google Cloud Console -> create a project -> enable **Gmail API** and **Google Calendar API**.
2. Create an **OAuth client (Desktop app)**, add your Gmail as a test user.
3. Save the client id/secret as `~/.campusinbox/client.json`:
   `{"client_id": "...", "client_secret": "..."}`
4. Gmail: `python3 -c "import sys; sys.path.insert(0,'../CampusInbox_MVP'); import gmail_auth; gmail_auth.login()"`
5. Calendar: `python3 -c "import google_calendar; google_calendar.login()"`
6. Use `provider="real"` in `make_gmail_search` / `make_calendar_events`. The agent still cannot send mail
   or write events.

## What was actually tested

- All 29 tests in `test_langgraph.py` pass offline (LangGraph graph, gate, tools, planner, demo, chat).
- The LangGraph engine's answers match the plain-Python loop on every test mail.
- NOT live-tested: real Gmail/Calendar sign-in (needs your laptop), real web search (needs
  `CAMPUS_WEB=1` + `CAMPUS_SEARCH_URL`), live WhatsApp/SMTP sending (needs your credentials).
