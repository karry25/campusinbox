"""Stream the CMU Enron maildir tarball and draw a seeded candidate pool.
Usage: python3 build_enron.py /path/to/enron_mail_20150507.tar.gz
Writes enron_pool.json (cue pool + no-cue pool). Deterministic: selection uses a hash of the Message-ID.
Source: https://www.cs.cmu.edu/~enron/ (public, widely cited corpus)."""
import sys, tarfile, email, re, json, hashlib
from email import policy
from email.utils import parsedate_to_datetime
CUE = re.compile(r"\b(deadline|due\s+(?:on|by|date)|no later than|rsvp|respond by|reply by|submit(?:ted)? by|"
                 r"by\s+(?:close of business|cob|eod|end of (?:the )?day|noon|tomorrow|monday|tuesday|wednesday|thursday|friday|"
                 r"\d{1,2}(?::\d{2})?\s?(?:am|pm|a\.m\.|p\.m\.))|before\s+(?:monday|tuesday|wednesday|thursday|friday|\d{1,2}/\d{1,2}))", re.I)
FOLDERS = {"inbox", "sent", "sent_items", "_sent_mail", "notes_inbox"}
CUT = re.compile(r"(-{3,}\s*Original Message\s*-{3,}|-{3,}\s*Forwarded by|^From:.*\n^Sent:|^On .* wrote:)", re.I | re.M)
def clean(body):
    m = CUT.search(body)
    if m: body = body[:m.start()]
    lines = [l for l in body.splitlines() if not l.lstrip().startswith(">")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
def h(s, mod): return int(hashlib.md5(s.encode()).hexdigest(), 16) % mod
def main(path):
    seen, cue, nocue, total = set(), [], [], 0
    with tarfile.open(path, "r|gz") as tf:
        for m in tf:
            if not m.isfile(): continue
            parts = m.name.split("/")
            if len(parts) < 4 or parts[-2].lower() not in FOLDERS: continue
            raw = tf.extractfile(m).read(); total += 1
            msg = email.message_from_bytes(raw, policy=policy.default)
            mid = (msg["Message-ID"] or m.name).strip()
            if mid in seen: continue
            seen.add(mid)
            try: dt = parsedate_to_datetime(msg["Date"])
            except Exception: continue
            bp = msg.get_body(preferencelist=("plain",))
            if bp is None: continue
            body = clean(bp.get_content())
            if not (150 <= len(body) <= 2500): continue
            subj = (msg["Subject"] or "").strip()
            rec = dict(id=hashlib.md5(mid.encode()).hexdigest()[:10], message_id=mid, date=dt.isoformat(), subject=subj, body=body, source=m.name)
            if CUE.search(subj + "\n" + body):
                if h(mid, 12) == 0: cue.append(rec)
            elif h(mid, 500) == 1: nocue.append(rec)
    json.dump(dict(files_scanned=total, unique=len(seen), cue_pool=cue, nocue_pool=nocue), open("enron_pool.json", "w"))
    print("scanned", total, "unique", len(seen), "cue", len(cue), "nocue", len(nocue))
main(sys.argv[1])
