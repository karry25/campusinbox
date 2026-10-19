# CampusInbox demo script
Kareena Jahagirdar | PRN 123B1B048 | Division A

## Before presenting
Extract the folder. Check Python 3.10+. Run `py app.py` on Windows or `python3 app.py` on Linux/macOS. Open http://127.0.0.1:8765. For a fresh demo, stop the server and delete campusinbox.db first. Restart. Keep the terminal open.

## 1. Explain the problem (20 seconds)
"College deadlines arrive in several mails. I wanted one place to check what is due, where the date came from, and what still needs my attention. CampusInbox keeps a record over time instead of answering a single chat message."

## 2. Load and inspect evidence (40 seconds)
Click Load sample mails. Five tasks appear, all in review.
Open the Autonomous assistant lab source. Show the exact Due line. Explain that the timestamp includes +05:30.
Click Approve deadline on the lab, Replication report and Search algorithms presentation. Leave the ambiguous project review unapproved.
"The offline demo uses strict parsing. It does not guess what 'next Friday' means. Every date needs my review before reminders are activated."

## 3. Show reminders and status (40 seconds)
Open Reminders. Show the overdue, within-24-hours and within-1-hour examples.
Return to Deadlines. The lab says Overdue - submission unverified.
Click Load sample Classroom status for the lab. It now says Missing (sample Classroom evidence).
"An email deadline is not proof of a missing submission. This button uses a synthetic Classroom fixture to demonstrate that distinction. It does not contact Classroom."

## 4. Show a safe reply draft (30 seconds)
Click Draft faculty reply. Edit one sentence, then Save draft edits. Refresh to show it persists.
"The draft does not invent an excuse. I can review and copy it, but the application has no Send function."
No teacher name or recipient address is supplied in this demo.

## 5. Change a deadline (30 seconds)
Open revision_mail.json in a text editor. Copy the whole JSON object into Import & clock, then click Import JSON.
Return to Deadlines. Replication report has version 2 and Needs review. Its old reminders are removed.
"A new version invalidates the old approval. The updated deadline cannot silently take effect."

## 6. Advance time and export (30 seconds)
Approve the new report date after reading its source. In Import & clock, set the demo clock to 2026-10-21T17:30:00+05:30. Open Reminders. The report receives the one-hour band. Refresh twice and show it does not duplicate.
Return to Deadlines. Click Export approved calendar (.ics). This is a file export, not a live Google Calendar write.

## 7. Close honestly (20 seconds)
"The local workflow runs and saves data in SQLite. Two roles separate evidence extraction from action planning, with deterministic code for scheduling and storage. The default is a no-key rules baseline. The optional LLM adapter is included but has not been tested against a live provider. OAuth sync, actual Classroom status and WhatsApp delivery are future integrations."

## Viva answers
**Where is the agent loop?** New mail import -> extraction proposal -> review pause -> state planning -> periodic reminder check -> persistent log -> new mail revision. Imports are manual in this MVP; the reminder worker runs independently every 15 seconds while the server is open.

**Why two roles?** The extractor deals with source evidence; the planner deals with next steps and drafts. Persistence, clock logic and sending permissions are not delegated to language generation. Two Python classes are role separation, not proof of two autonomous LLM agents.

**Why not use more agents?** Parsing, time comparisons and duplicate checks do not need a separate agent. Extra reasoning roles would add overhead without solving a distinct problem.

**What was tested?** The bundled test report lists 23 offline unit tests, the browser walkthrough and an isolated HTTP/restart demo. Real APIs and a live model were not tested.

**What if a mail says to reveal private data?** Mail is displayed as text, not executed. The model has no tools. No external send action exists. The security sample demonstrates this boundary; it is not a complete adversarial evaluation.

**What if the app is closed?** Reminders are not delivered while the server is stopped. Current state is caught up when reopened, but this is not an always-on service.
