"""User-run, read-only Gmail access (standard library only). OFF by default. Implemented, NOT live-tested.

You create your own OAuth client in Google Cloud (Desktop app) and put the client id and secret in
~/.campusinbox/client.json as {"client_id": "...", "client_secret": "..."}. Nothing is shipped in this project.
Only the gmail.readonly scope is requested. There is no code that sends mail. The token is stored in
~/.campusinbox/token.json with mode 0600, outside the project folder."""
import base64
import hashlib
import json
import os
import secrets
import urllib.parse
import urllib.request
from pathlib import Path

SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
HOME = Path(os.getenv("CAMPUS_HOME", str(Path.home() / ".campusinbox")))


def auth_url(client_id, redirect_uri, state, challenge):
    q = {"client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code", "scope": SCOPE, "access_type": "offline",
         "state": state, "code_challenge": challenge, "code_challenge_method": "S256"}
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(q)


def pkce():
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def save_token(token):
    HOME.mkdir(parents=True, exist_ok=True)
    p = HOME / "token.json"
    fd = os.open(str(p), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(token, f)
    os.chmod(str(p), 0o600)
    return p


def login(open_browser=True):
    """Loopback OAuth flow with PKCE. Prints the URL; the user signs in with their own Google account."""
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import webbrowser
    cfg = json.loads((HOME / "client.json").read_text())
    got = {}

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200); self.end_headers(); self.wfile.write(b"CampusInbox: you can close this tab.")
        def log_message(self, *a): pass
    srv = HTTPServer(("127.0.0.1", 0), H)
    redirect = "http://127.0.0.1:%d" % srv.server_port
    verifier, challenge = pkce(); state = secrets.token_urlsafe(16)
    url = auth_url(cfg["client_id"], redirect, state, challenge)
    print("Open this URL and sign in with your own Google account (read-only access):\n" + url)
    if open_browser:
        webbrowser.open(url)
    srv.handle_request()
    if got.get("state") != state or "code" not in got:
        raise RuntimeError("Sign-in was not completed.")
    data = urllib.parse.urlencode({"code": got["code"], "client_id": cfg["client_id"], "client_secret": cfg["client_secret"],
                                   "redirect_uri": redirect, "grant_type": "authorization_code", "code_verifier": verifier}).encode()
    with urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=data), timeout=20) as r:
        return save_token(json.loads(r.read()))


def _b64(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)).decode("utf-8", "replace")


def message_to_mail(msg):
    """Gmail API message resource (format=full) -> CampusInbox mail dict. Plain text parts only."""
    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
    def find(part):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return _b64(part["body"]["data"])
        for p in part.get("parts", []) or []:
            r = find(p)
            if r:
                return r
        return None
    body = find(msg.get("payload", {}))
    if not body:
        return None
    mail = {"id": "gmail:" + msg["id"], "subject": headers.get("subject", "(no subject)"), "body": body}
    if headers.get("date"):
        from email.utils import parsedate_to_datetime
        try:
            mail["date"] = parsedate_to_datetime(headers["date"]).isoformat()
        except (TypeError, ValueError):
            pass
    return mail


def fetch_recent(max_n=20, query="newer_than:14d", opener=urllib.request.urlopen, token=None):
    """List and read recent messages. Read-only. Returns mails; the caller imports them through the normal review gate."""
    token = token or json.loads((HOME / "token.json").read_text())["access_token"]
    def get(url):
        with opener(urllib.request.Request(url, headers={"Authorization": "Bearer " + token}), timeout=20) as r:
            return json.loads(r.read())
    base = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
    ids = get(base + "?" + urllib.parse.urlencode({"q": query, "maxResults": min(max_n, 50)})).get("messages", [])
    mails = [message_to_mail(get(base + "/" + i["id"] + "?format=full")) for i in ids]
    return [m for m in mails if m]
