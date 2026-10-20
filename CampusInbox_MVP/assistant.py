"""CampusInbox assistant helpers (standard library only): mailbox search, priority, conflicts, weekly digest, notifier adapters.
Notifier adapters other than console and file are OFF by default and implemented but not live-tested."""
import json
import math
import os
import re
import urllib.request
from datetime import timedelta


# ---- retrieval over the local mailbox (BM25, no embeddings) ----
def _tok(text):
    return re.findall(r"[a-z0-9]+", text.lower())


STOP = set("a an the is are was were be to of in on at for and or what whats did do does about say said tell me my any when which who how can could please".split())


def bm25_search(mails, query, k=5, k1=1.5, b=0.75):
    """mails: list of dicts with id, subject, body. Returns [(score, mail_id, subject)] best first."""
    docs = [(m["id"], m["subject"], _tok(m["subject"] + " " + m["subject"] + " " + m["body"])) for m in mails]
    q = {w for w in _tok(query) if w not in STOP}
    if not docs or not q:
        return []
    avg = sum(len(t) for _, _, t in docs) / len(docs) or 1
    n = len(docs)
    df = {w: sum(1 for _, _, t in docs if w in t) for w in q}
    out = []
    for mid, subj, toks in docs:
        score = 0.0
        for w in q:
            f = toks.count(w)
            if f:
                idf = math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5))
                score += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * len(toks) / avg))
        if score > 0:
            out.append((round(score, 4), mid, subj))
    return sorted(out, reverse=True)[:k]


# ---- priority, conflicts, digest (deterministic, on approved tasks only) ----
def priority(tasks, clock, stamp):
    """Rank approved, not-submitted tasks: overdue first, then soonest. Returns [(rank, label, task)]."""
    live = [t for t in tasks if not t["review"] and t["due_at"] and t["status"] != "TURNED_IN"]
    live.sort(key=lambda t: stamp(t["due_at"]))
    out = []
    for i, t in enumerate(live, 1):
        hours = (stamp(t["due_at"]) - clock).total_seconds() / 3600
        label = "overdue" if hours <= 0 else "urgent (under 24 h)" if hours <= 24 else "this week" if hours <= 168 else "later"
        out.append((i, label, t))
    return out


def conflicts(tasks, stamp, window_hours=3):
    """Pairs of approved, not-submitted tasks due within window_hours of each other."""
    live = [t for t in tasks if not t["review"] and t["due_at"] and t["status"] != "TURNED_IN"]
    live.sort(key=lambda t: stamp(t["due_at"]))
    out = []
    for a, b in zip(live, live[1:]):
        gap = (stamp(b["due_at"]) - stamp(a["due_at"])).total_seconds() / 3600
        if gap <= window_hours:
            out.append((a["title"], b["title"], round(gap, 2)))
    return out


def weekly_digest(tasks, clock, stamp):
    ranked = [(r, l, t) for r, l, t in priority(tasks, clock, stamp) if l != "later"]
    lines = ["CampusInbox digest (sample data in demo mode)"]
    if not ranked:
        lines.append("Nothing due in the next 7 days.")
    for r, label, t in ranked:
        lines.append("%d. [%s] %s - %s, due %s" % (r, label, t["course"], t["title"], stamp(t["due_at"]).strftime("%d %b %H:%M %z")))
    cf = conflicts(tasks, stamp)
    for a, b, gap in cf:
        lines.append("Conflict: '%s' and '%s' are %.1f h apart." % (a, b, gap))
    review = sum(1 for t in tasks if t["review"])
    if review:
        lines.append("%d task(s) still need your review; no reminders for them yet." % review)
    return "\n".join(lines)


# ---- notifier adapters (reminders to the owner only; never faculty) ----
class ConsoleNotifier:
    name = "console"

    def send(self, text):
        print(text)
        return True


class FileNotifier:
    name = "file"

    def __init__(self, path):
        self.path = path

    def send(self, text):
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(text + "\n")
        return True


class WhatsAppCloudNotifier:
    """Meta WhatsApp Cloud API, to the owner's own number. Off unless CAMPUS_WA_TOKEN, CAMPUS_WA_PHONE_ID and CAMPUS_WA_TO are set.
    Implemented, NOT live-tested. dry_run=True by default: builds the request but does not send."""
    name = "whatsapp"

    def __init__(self, token, phone_id, to, dry_run=True, opener=urllib.request.urlopen):
        self.token, self.phone_id, self.to, self.dry_run, self.opener = token, phone_id, to, dry_run, opener

    def build(self, text):
        url = "https://graph.facebook.com/v20.0/%s/messages" % self.phone_id
        body = {"messaging_product": "whatsapp", "to": self.to, "type": "text", "text": {"body": text[:1000]}}
        return url, body

    def send(self, text):
        url, body = self.build(text)
        if self.dry_run:
            return False
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Authorization": "Bearer " + self.token, "Content-Type": "application/json"})
        with self.opener(req, timeout=20) as r:
            return 200 <= r.status < 300


class EmailNotifier:
    """SMTP, to the owner's own address. Off unless CAMPUS_SMTP_HOST, CAMPUS_SMTP_USER, CAMPUS_SMTP_PASS, CAMPUS_MAIL_TO are set.
    Implemented, NOT live-tested. dry_run=True by default."""
    name = "email"

    def __init__(self, host, user, password, to, dry_run=True, smtp_cls=None):
        self.host, self.user, self.password, self.to, self.dry_run, self.smtp_cls = host, user, password, to, dry_run, smtp_cls

    def send(self, text):
        if self.dry_run:
            return False
        import smtplib
        from email.message import EmailMessage
        m = EmailMessage()
        m["From"], m["To"], m["Subject"] = self.user, self.to, "CampusInbox reminder"
        m.set_content(text)
        with (self.smtp_cls or smtplib.SMTP_SSL)(self.host) as s:
            s.login(self.user, self.password)
            s.send_message(m)
        return True


def notifiers_from_env(file_path=None, console=True):
    """Console is always available. Others need explicit env config AND CAMPUS_NOTIFY_LIVE=1, otherwise dry run."""
    live = os.getenv("CAMPUS_NOTIFY_LIVE") == "1"
    out = [FileNotifier(file_path)] if file_path else ([ConsoleNotifier()] if console else [])
    if all(os.getenv(k) for k in ("CAMPUS_WA_TOKEN", "CAMPUS_WA_PHONE_ID", "CAMPUS_WA_TO")):
        out.append(WhatsAppCloudNotifier(os.environ["CAMPUS_WA_TOKEN"], os.environ["CAMPUS_WA_PHONE_ID"], os.environ["CAMPUS_WA_TO"], dry_run=not live))
    if all(os.getenv(k) for k in ("CAMPUS_SMTP_HOST", "CAMPUS_SMTP_USER", "CAMPUS_SMTP_PASS", "CAMPUS_MAIL_TO")):
        out.append(EmailNotifier(os.environ["CAMPUS_SMTP_HOST"], os.environ["CAMPUS_SMTP_USER"], os.environ["CAMPUS_SMTP_PASS"], os.environ["CAMPUS_MAIL_TO"], dry_run=not live))
    return out
