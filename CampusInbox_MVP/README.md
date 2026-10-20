# CampusInbox - working local MVP
Kareena Jahagirdar | PRN 123B1B048 | Division A

CampusInbox turns sample college mails into reviewed deadlines, an exportable calendar, in-app reminders and faculty-reply drafts. The app stores its work between restarts. It has no mail-send function.

## Start here (Windows)
1. Download CampusInbox_MVP.zip from the project Drive folder.
2. Right-click the ZIP and choose Extract All. Open the extracted folder.
3. You need Python 3.10 or newer. In Command Prompt, check: `py --version`.
4. Double-click `start_windows.bat`, or open Command Prompt in this folder and run:

```bat
py app.py
```

5. Keep the terminal open. Open this exact address in Chrome or Edge:

```
http://127.0.0.1:8765
```

6. Click **Load sample mails**. Open the source mail, check its date, then click **Approve deadline**. Reminders appear in the Reminders tab.
7. Press Ctrl+C in the terminal to stop. Do not open index.html by double-clicking it: the Python server is required.

No pip install, API key or Google login is needed for the default demo.
If `py` is not available but `python --version` works, use `python app.py` instead. If neither exists, install Python 3.10+ first. Setup on a Windows laptop has not been tested here; the app was executed on Linux with Python 3.10 and Chrome.

## macOS / Linux
```sh
cd CampusInbox_MVP
python3 app.py
```
Open http://127.0.0.1:8765. Stop with Ctrl+C.

Port busy? Use `py app.py --port 8766` (or `python3`) and open http://127.0.0.1:8766.

## Three-minute demo
Read DEMO_SCRIPT.md. The initial demo clock is fixed at **19 October 2026, 9 PM IST**, regardless of today's date. This makes the sample reminders repeatable. It does not change the computer clock.

- Five synthetic mails cover an overdue lab, a next-day report, a 45-minute deadline, an ambiguous date and an untrusted instruction.
- Every extracted deadline starts in review. No reminder is created before approval.
- Open **Read source mail / evidence** to see the source and verbatim deadline quote.
- Approve the three ordinary deadlines. The 24-hour, 1-hour and overdue bands appear as in-app reminders.
- **Load sample Classroom status** deliberately loads synthetic evidence, not Classroom data. Without it, the overdue lab says submission unverified, not missing.
- **Draft faculty reply** creates editable local text. **Save draft edits** persists changes. Copy it for review if needed. There is no recipient field or Send button.
- Paste revision_mail.json into Import & clock. The revised report becomes version 2, requires review again and drops old reminders.
- Export approved deadlines with **Export approved calendar (.ics)**. This downloads a standard calendar file, not a Google Calendar integration. Only approved deadlines are included. Export again after revisions. Do not repeatedly import old files into a real calendar without checking how that calendar handles updates and duplicate UIDs.

## Tests
Windows:
```bat
py -m unittest -v
```
macOS / Linux:
```sh
python3 -m unittest -v
```
The suite (`test_app.py`, `test_agent.py`, `test_assistant.py`, `test_chatbot.py`) has 74 offline tests; all pass. No test calls a real model or Gmail. TEST_REPORT.md records what was actually executed. `demo_walkthrough.py` runs an additional HTTP-level demo in a temporary database, including server restart persistence, without touching your normal app data:
```bat
py demo_walkthrough.py
```

## Files
- app.py: HTTP API, SQLite schema, extractor and planner roles, review gate, reminders, .eml import and calendar export.
- index.html / style.css / app.js: plain black-and-white responsive UI.
- sample_mails.json: five clearly synthetic mails.
- revision_mail.json: a sample deadline-change import object.
- test_app.py: standard-library unit tests.
- demo_walkthrough.py: isolated end-to-end HTTP demo.
- start_windows.bat / start_unix.sh: launcher helpers.
- DEMO_SCRIPT.md: presentation order and viva explanation.
- TEST_REPORT.md: actual test evidence and known limits.
- 01...05 PNG files: screenshots of this version running, not UI mockups.

## Architecture in the code
EvidenceExtractor reads source content and proposes a deadline with evidence. ActionPlanner decides safe next-state labels and produces a reply draft. Both are Python role boundaries, not two separate chatbots. Ordinary code handles persistence, deduplication, the clock, HTTP, review requirements, reminder timing and retries.

The default mode is an **offline rules baseline**, not a live LLM or a claim of fully autonomous AI. It recognizes explicit lines named `Course:`, `Task:` and `Due:`. `Due:` must contain a full ISO timestamp and timezone, for example `2026-10-20T18:00:00+05:30`. Ordinary free-form dates stay in review. It does not understand every real college email.

A human can enter an exact verified date for an ambiguous mail and approve it. A changed assignment is matched only by an explicit `assignment_key`; automatic fuzzy matching is intentionally absent. Retained older source mails and the activity log let you inspect how a revision arrived. Every revision is held for approval, even when its date looks familiar. Older reminder records for that task are removed so they cannot act on a superseded deadline.

## Agent features, chat and what is tested (read this before claiming anything)
| Feature | Status |
|---|---|
| Tool loop (read_header, search_mail, read_context, parse_date, check_quote), step cap, reflection retry, Verifier, logged messages | Built, unit-tested with a mock model; offline scripted run needs no model. Live model run only on Enron/synthetic mail (see paper) |
| BM25 retrieval, chat panel (mails + syllabus, source line shown, "not found") | Built, unit-tested (hit, no answer, injection in mail, fabricated quote) |
| Priority, conflicts, weekly digest (`--digest`) | Built, unit-tested |
| Console and file notifiers | Built, tested |
| WhatsApp Cloud and email reminder adapters | Stub, dry-run unless CAMPUS_NOTIFY_LIVE=1 and your own keys; never run against the real services |
| Gmail read-only import (`--gmail-login`, `--gmail-import N`) | Implemented, not live-tested. Read-only scope, token kept in ~/.campusinbox (mode 0600), nothing in this folder. No send code exists |
| Classroom/Calendar sync, embeddings, learned planner, user study | Planned, not built |

Agent mode: set CAMPUS_MODEL_URL, CAMPUS_MODEL_NAME, CAMPUS_ENGINE=agent (and CAMPUS_MODEL_KEY if needed). Chat model mode: also CAMPUS_CHAT_MODEL=1. Without these everything runs offline. Use synthetic mail until you decide to share real mail with your provider. The models are prompted, not trained; there is no trained classifier in this project.

## Optional LLM proposal mode (not live-provider tested)
The same two roles can call a user-selected OpenAI-compatible chat-completions endpoint. No provider account, key, model download or billed request is included. Endpoint compatibility varies.

Set these environment variables **before starting the server**:
- CAMPUS_MODEL_URL: complete HTTPS chat-completions URL, or an HTTP loopback URL for a local server.
- CAMPUS_MODEL_NAME: model name supported by that server.
- CAMPUS_MODEL_KEY: optional provider secret, only if required. Keep it in your local environment, never in this project, screenshots or chat.

The adapter sends subject/body to the selected endpoint during import, and task title/course/deadline during drafting. Use only synthetic data until you have evaluated that provider's privacy settings and explicitly decided to share real content. The app does not send stored mail anywhere in offline mode. There is no fallback to an external provider on failure.

Extractor responses must contain `due_at` plus a literal `quote` containing that exact date in the input, or a null date when absent. Invalid evidence rejects the import. Every accepted suggestion still needs review. The planner returns a draft only. Model tools, mail sending and status mutation are not available to it. A timeout/failure rolls the import transaction back; retry manually after fixing setup. Do not describe the mock-adapter tests as proof that a live LLM worked.

## Import other exported samples
Paste JSON in the Import & clock tab:
```json
{"mails":[{"id":"unique-message-1","assignment_key":"unique-assignment","subject":"Sample assignment","body":"Course: Agentic AI\nTask: Demo report\nDue: 2026-10-23T17:00:00+05:30"}]}
```
A repeated identical message ID is ignored. Reusing an ID with different content is rejected. A new message with the same assignment_key is a revision. Different tasks must use different assignment keys. Import batches are atomic, limited to 50 mails and 250 KB total HTTP body.

Plain-text .eml files can also be imported from the terminal while the server is stopped:
```bat
py app.py --import-eml sample.eml
```

Bulk import (read-only, offline, nothing is sent):

    py app.py --import-dir path/to/folder_of_eml_files
    py app.py --import-mbox path/to/export.mbox

Local reminder notifier (same worker as the page; prints reminders not announced before, approved tasks only):

    py app.py --notify --notify-file reminders.txt

Run it from Task Scheduler or cron. It is a text notification, not push, e-mail or WhatsApp.

The importer takes a plain-text body and ignores attachments/HTML-only content. It is not an inbox watcher. No OAuth connection is present.

## Persistence, reminders and reset
The app creates `campusinbox.db` beside app.py. It contains source mails, tasks, draft text, reminder records and the audit log. Do not upload this database if you later use private data. Stop the app before backing up or deleting it.

The worker checks every 15 seconds while the terminal process runs. In live-clock mode it uses device time. In fixed demo mode it keeps checking the chosen simulated time until you change it. UI data refreshes once per minute, or click Refresh. Only the most relevant band is emitted when the clock jumps; it does not backfill every missed band. Stored reminders are an event history, not repeated messages. Repeated checks do not recreate the same task/version/band. Submitted tasks are suppressed. Stopping the server stops background work; on restart, the current band can be caught up, but closed-process timing is not guaranteed.

To reset: stop the app, delete `campusinbox.db`, restart. No real account, email or calendar item is changed by resetting this local database. Screenshots are demo evidence only and do not load automatically as app data.

## Privacy and scope
Local loopback binding, host validation, a per-run request token, text-only DOM insertion, a restrictive content-security policy and atomic DB transactions are included. These are demo protections, not a production security audit. The app has no user login or encrypted database; other people with local computer access can read it. Do not expose it to the network, host it publicly or use it as a multi-user service.

Not implemented: continuous Gmail/Classroom sync, OAuth, real submission verification, Google Calendar writes, WhatsApp delivery, email sending, attachment analysis, malware scanning, robust natural-language date interpretation, multi-user roles and production deployment. All sample Classroom evidence is explicitly synthetic. A returned/graded state is not inferred as submitted. The full architecture pack describes future work, not features already deployed here.
