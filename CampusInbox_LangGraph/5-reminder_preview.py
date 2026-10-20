"""Reminder tool in PREVIEW mode: shows the exact WhatsApp / email reminder the agent would send,
without sending anything. Live sending adapters already exist in the MVP (assistant.WhatsAppCloudNotifier /
EmailNotifier, dry_run=True by default); they are implemented, need the student's own credentials, and are
NOT live-tested. This tool never sends."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "CampusInbox_MVP"))
from assistant import WhatsAppCloudNotifier
from langchain_core.tools import StructuredTool

PREVIEW = ("PREVIEW ONLY - nothing was sent. Live WhatsApp/SMTP sending is implemented in the app but "
           "needs your own credentials (CAMPUS_WA_* / CAMPUS_SMTP_* plus CAMPUS_NOTIFY_LIVE=1) and is not live-tested.")


def reminder_text(title, date_iso, human_time_left):
    return ("CampusInbox reminder: \"%s\" is due on %s (%s). Reply done when submitted."
            % (title[:80], date_iso, human_time_left))


def make_reminder_tool(today=None):
    def propose_reminder(title: str, date_iso: str, human_time_left: str = "") -> str:
        """Preview the reminder message for an approved deadline. Never sends; the student reviews the text."""
        text = reminder_text(title, date_iso, human_time_left or "see calendar")
        url, body = WhatsAppCloudNotifier("(token)", "(phone-id)", "(your-number)", dry_run=True).build(text)
        return json.dumps({"status": PREVIEW,
                           "whatsapp_preview": {"api": url, "payload": body},
                           "email_preview": {"subject": "CampusInbox reminder", "body": text},
                           "console_preview": text})
    return StructuredTool.from_function(propose_reminder)
