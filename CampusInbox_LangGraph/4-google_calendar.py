"""User-run, READ-ONLY Google Calendar access (standard library only). OFF by default. NOT live-tested here.

Uses the same OAuth client file as gmail_auth (~/.campusinbox/client.json) but its own token file
(~/.campusinbox/calendar_token.json) with the calendar.readonly scope. There is NO event-write function
in this project: new events are proposals only - the tool returns a Google Calendar "add event" link
that the student clicks themselves, so every calendar change needs a human action."""
import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from gmail_auth import HOME, auth_url, pkce, save_token  # same OAuth helpers as the Gmail sign-in

SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
TOKEN_FILE = "calendar_token.json"


def save_cal_token(token):
    HOME.mkdir(parents=True, exist_ok=True)
    p = HOME / TOKEN_FILE
    import os
    fd = os.open(str(p), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(token, f)
    return p


def login(open_browser=True):
    """Same loopback OAuth flow as gmail_auth.login, with the calendar.readonly scope."""
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import webbrowser
    cfg = json.loads((HOME / "client.json").read_text())
    got = {}

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200); self.end_headers(); self.wfile.write(b"CampusInbox calendar: you can close this tab.")
        def log_message(self, *a): pass
    srv = HTTPServer(("127.0.0.1", 0), H)
    redirect = "http://127.0.0.1:%d" % srv.server_port
    verifier, challenge = pkce(); state = __import__("secrets").token_urlsafe(16)
    url = auth_url(cfg["client_id"], redirect, state, challenge).replace(
        urllib.parse.quote_plus("https://www.googleapis.com/auth/gmail.readonly"), urllib.parse.quote_plus(SCOPE))
    print("Open this URL and sign in with your own Google account (read-only calendar access):\n" + url)
    if open_browser:
        webbrowser.open(url)
    srv.handle_request()
    if got.get("state") != state or "code" not in got:
        raise RuntimeError("Sign-in was not completed.")
    data = urllib.parse.urlencode({"code": got["code"], "client_id": cfg["client_id"], "client_secret": cfg["client_secret"],
                                   "redirect_uri": redirect, "grant_type": "authorization_code", "code_verifier": verifier}).encode()
    with urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=data), timeout=20) as r:
        return save_cal_token(json.loads(r.read()))


def list_events(days=7, opener=urllib.request.urlopen, token=None):
    """Read the primary calendar's events for the next `days` days. Read-only."""
    token = token or json.loads((HOME / TOKEN_FILE).read_text())["access_token"]
    now = datetime.now(timezone.utc)
    q = urllib.parse.urlencode({"timeMin": now.isoformat().replace("+00:00", "Z"),
                                "timeMax": (now + timedelta(days=days)).isoformat().replace("+00:00", "Z"),
                                "singleEvents": "true", "orderBy": "startTime", "maxResults": 25})
    req = urllib.request.Request("https://www.googleapis.com/calendar/v3/calendars/primary/events?" + q,
                                 headers={"Authorization": "Bearer " + token})
    with opener(req, timeout=20) as r:
        items = json.loads(r.read()).get("items", [])
    return [{"summary": e.get("summary", "(no title)"),
             "start": (e.get("start") or {}).get("dateTime") or (e.get("start") or {}).get("date"),
             "end": (e.get("end") or {}).get("dateTime") or (e.get("end") or {}).get("date")} for e in items]


def propose_link(title, date_iso, details=""):
    """A Google Calendar 'add event' LINK. Clicking it is the student's own action; this code writes nothing."""
    d = date_iso.replace("-", "")
    q = urllib.parse.urlencode({"action": "TEMPLATE", "text": title, "dates": "%s/%s" % (d, d),
                                "details": details})
    return "https://calendar.google.com/calendar/render?" + q
