import base64
import json
import os
import stat
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
import assistant as S
import gmail_auth as G

IST = timezone(timedelta(hours=5, minutes=30))
stamp = lambda v: datetime.fromisoformat(v)
CLOCK = datetime(2026, 10, 19, 21, 0, tzinfo=IST)


def T(i, title, due, review=0, status="UNKNOWN"):
    return {"id": i, "course": "C", "title": title, "due_at": due, "review": review, "status": status}


class SearchTests(unittest.TestCase):
    def test_bm25_ranks_relevant_mail_first(self):
        mails = [{"id": "a", "subject": "Lab", "body": "replication report due friday"}, {"id": "b", "subject": "Lunch", "body": "pizza at noon"}]
        r = S.bm25_search(mails, "replication report")
        self.assertEqual(r[0][1], "a"); self.assertEqual(len(r), 1)
        self.assertEqual(S.bm25_search(mails, "zzz"), [])


class PlanTests(unittest.TestCase):
    tasks = [T("1", "A", "2026-10-20T10:00:00+05:30"), T("2", "B", "2026-10-20T11:30:00+05:30"), T("3", "C", "2026-10-19T20:00:00+05:30"),
             T("4", "D", "2026-10-30T10:00:00+05:30"), T("5", "E", "2026-10-20T10:30:00+05:30", review=1), T("6", "F", "2026-10-20T10:20:00+05:30", status="TURNED_IN")]

    def test_priority_order_and_labels(self):
        r = S.priority(self.tasks, CLOCK, stamp)
        self.assertEqual([t["title"] for _, _, t in r], ["C", "A", "B", "D"])
        self.assertEqual([l for _, l, _ in r], ["overdue", "urgent (under 24 h)", "urgent (under 24 h)", "later"])

    def test_conflicts_skip_review_and_submitted(self):
        self.assertEqual(S.conflicts(self.tasks, stamp), [("A", "B", 1.5)])

    def test_digest_mentions_review_and_conflict(self):
        d = S.weekly_digest(self.tasks, CLOCK, stamp)
        self.assertIn("Conflict", d); self.assertIn("still need your review", d); self.assertNotIn("D", d.split("\n")[1])


class NotifierTests(unittest.TestCase):
    def test_file_notifier(self):
        p = Path(tempfile.mkdtemp()) / "r.txt"
        self.assertTrue(S.FileNotifier(str(p)).send("hello")); self.assertEqual(p.read_text(), "hello\n")

    def test_whatsapp_and_email_are_dry_run_by_default(self):
        called = []
        wa = S.WhatsAppCloudNotifier("tok", "123", "+910000000000", opener=lambda *a, **k: called.append(1))
        self.assertFalse(wa.send("x")); self.assertFalse(called)
        url, body = wa.build("x"); self.assertIn("/123/messages", url); self.assertEqual(body["to"], "+910000000000")
        em = S.EmailNotifier("h", "u@x", "pw", "me@x", smtp_cls=lambda h: called.append(2))
        self.assertFalse(em.send("x")); self.assertFalse(called)

    def test_env_needs_all_keys_and_live_flag(self):
        for k in list(os.environ):
            if k.startswith("CAMPUS_WA") or k.startswith("CAMPUS_SMTP") or k in ("CAMPUS_NOTIFY_LIVE", "CAMPUS_MAIL_TO"): os.environ.pop(k)
        self.assertEqual([n.name for n in S.notifiers_from_env()], ["console"])
        os.environ.update({"CAMPUS_WA_TOKEN": "t", "CAMPUS_WA_PHONE_ID": "1", "CAMPUS_WA_TO": "+91"})
        try:
            ns = S.notifiers_from_env(); self.assertEqual([n.name for n in ns], ["console", "whatsapp"]); self.assertTrue(ns[1].dry_run)
            os.environ["CAMPUS_NOTIFY_LIVE"] = "1"; self.assertFalse(S.notifiers_from_env()[1].dry_run)
        finally:
            for k in ("CAMPUS_WA_TOKEN", "CAMPUS_WA_PHONE_ID", "CAMPUS_WA_TO", "CAMPUS_NOTIFY_LIVE"): os.environ.pop(k, None)


class GmailTests(unittest.TestCase):
    def test_auth_url_is_read_only_with_pkce(self):
        v, c = G.pkce(); u = G.auth_url("cid", "http://127.0.0.1:1", "st", c)
        self.assertIn("gmail.readonly", u); self.assertNotIn("gmail.send", u); self.assertIn("code_challenge_method=S256", u)

    def test_token_file_mode_is_private(self):
        G.HOME = Path(tempfile.mkdtemp()) / "ci"
        p = G.save_token({"access_token": "x"}); self.assertEqual(stat.S_IMODE(p.stat().st_mode), 0o600)

    def test_message_to_mail_parses_plain_text_and_date(self):
        data = base64.urlsafe_b64encode(b"Due: 2026-10-23T17:00:00+05:30").decode().rstrip("=")
        msg = {"id": "m1", "payload": {"headers": [{"name": "Subject", "value": "Lab"}, {"name": "Date", "value": "Mon, 19 Oct 2026 10:00:00 +0530"}],
               "parts": [{"mimeType": "text/html", "body": {"data": "eA"}}, {"mimeType": "text/plain", "body": {"data": data}}]}}
        m = G.message_to_mail(msg)
        self.assertEqual(m["id"], "gmail:m1"); self.assertIn("2026-10-23", m["body"]); self.assertTrue(m["date"].startswith("2026-10-19"))
        self.assertIsNone(G.message_to_mail({"id": "m2", "payload": {"headers": [], "parts": [{"mimeType": "text/html", "body": {"data": "eA"}}]}}))

    def test_fetch_recent_with_fake_transport_is_read_only(self):
        urls = []
        class R:
            def __init__(s, d): s.d = json.dumps(d).encode()
            def read(s): return s.d
            def __enter__(s): return s
            def __exit__(s, *a): pass
        data = base64.urlsafe_b64encode(b"hello").decode().rstrip("=")
        def opener(req, timeout=0):
            urls.append(req.full_url)
            if "format=full" in req.full_url:
                return R({"id": "m1", "payload": {"headers": [{"name": "Subject", "value": "S"}], "mimeType": "text/plain", "body": {"data": data}}})
            return R({"messages": [{"id": "m1"}]})
        mails = G.fetch_recent(opener=opener, token="t")
        self.assertEqual(len(mails), 1); self.assertTrue(all(u.startswith("https://gmail.googleapis.com/") and "send" not in u for u in urls))


if __name__ == "__main__":
    unittest.main()
