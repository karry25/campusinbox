# CampusInbox test report
Kareena Jahagirdar | PRN 123B1B048 | Division A

Executed on 19 October 2026 on Linux, Python 3.10 and headless Google Chrome. All input mails were synthetic. No live LLM, Google account, Classroom account, Google Calendar or WhatsApp API was used.

## Automated unit tests: 74 passed (updated 21 October 2026; this report's numbered list shows the original 23)
Command: `python3 -m unittest -v`

1. Explicit timezone-aware date and verbatim quote extraction.
2. Ambiguous date remains unapproved.
3. Unreviewed dates produce no reminders.
4. Repeated message import is deduplicated.
5. Conflicting content with the same message ID is rejected.
6. 24-hour, 1-hour and overdue reminder bands each emit once.
7. Student-reported submission suppresses reminders.
8. Email deadline alone does not prove a missing submission.
9. Synthetic Classroom evidence is labelled as synthetic.
10. Deadline revision invalidates approval and removes old reminders.
11. User status endpoint cannot claim a Classroom NOT_SUBMITTED state.
12. Draft is persisted; send endpoint is absent.
13. Draft edits are stored.
14. Calendar includes only approved events, converts to UTC and folds lines.
15. Naive timestamps without timezone are rejected.
16. Data persists across database reconnections.
17. Instructions in a mail remain data; no send is triggered.
18. Mock model response with invented evidence is rejected.
19. Mock model response with a valid quote is accepted as a proposal.
20. Mock model response can abstain on an ambiguous date.
21. Bad mail in a batch rolls back the whole import.
22. Plain-text .eml import works.
23. Non-object mail input is rejected.

The three model tests replace the adapter with controlled mock output. They test validation, not a live model's quality, prompt-injection resistance or endpoint compatibility.

## Isolated HTTP walkthrough: 8 checks passed
Command: `python3 demo_walkthrough.py`

- Five samples import with a review gate and no reminders.
- Three approved deadlines produce the intended reminder bands.
- Re-import and refresh do not duplicate tasks/reminders.
- Email-only status and synthetic Classroom status remain distinct.
- Revision replaces the active deadline, requires review and drops obsolete reminders.
- An actual process stop/restart preserves edited draft and revised version.
- Calendar export excludes tasks that need review.
- The send endpoint does not exist.

This script starts an isolated server on a temporary port, uses a temporary SQLite database and cleans up afterward. It is included so the demo can be repeated.

## Chrome browser walkthrough: passed
The actual running app was opened and operated in Chrome:
- Load five samples, inspect five rendered task cards.
- Approve three deadlines using UI controls.
- Load synthetic Classroom evidence and check its label.
- Create a draft, edit it, save it and reload the page to confirm persistence.
- Open Reminders and confirm three entries.
- Import a revision through the UI and confirm version 2 / Needs review.
- Check no horizontal overflow at 390px and 320px viewport widths.
- Check no JavaScript page errors during the walkthrough.
- Confirm a POST without the local request token receives HTTP 403.
- Download the calendar endpoint and check the approved event count.
- Remove a reminder directly from the test database, make no API requests, wait 16 seconds and confirm the server's worker recreates the relevant band. This verifies that scheduling is not only a side effect of refreshing the UI.

Five PNG screenshots record this running version. Desktop and phone images were visually inspected for readable sections, wrapping and clipping. The UI is deliberately black and white. No evidence screenshot is a fabricated mockup.

## Not tested or implemented
- Windows/macOS execution: launchers and steps are provided but were not run on those operating systems.
- Python versions other than the installed 3.10 runtime.
- Live LLM calls, model-provider compatibility, model accuracy or billed requests.
- OAuth, Gmail push/sync, attachment extraction and real Classroom submission verification.
- Google Calendar API writes, calendar-app import/update behavior, WhatsApp delivery or email sends.
- Production deployment, encrypted storage, multi-user access, penetration testing and all-day reliability.
- Complete adversarial testing. One synthetic hostile-content sample does not prove that all model prompt injections are blocked.

The app is a working local workflow MVP. It is not an always-on inbox service and must not be described as a deployed fully autonomous AI agent.


## LangGraph extension tests: 35 passed (21 October 2026)
Command: `python3 test_langgraph.py` in the CampusInbox_LangGraph folder. Offline; no API key, account or network. Covers the LangGraph agent graph (agreement with the plain loop on every test mail), the quote gate, the date calculator, demo inbox, proposal-only calendar, reminder preview, planner graph, demo mode and chat citations. Live Gmail, Calendar, web search and WhatsApp/SMTP delivery are not tested.
