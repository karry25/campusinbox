"""CampusInbox rules v2: deadline extraction from free text, anchored to the mail's Date header.
Precision first: it abstains when a deadline sentence holds zero or several different dates, or when
the date needs a convention call (e.g. 'next Friday', or a bare weekday equal to the mail's weekday)."""
import re
from datetime import date, timedelta
MONTHS = {m: i + 1 for i, m in enumerate("january february march april may june july august september october november december".split())}
MABBR = {k[:3]: v for k, v in MONTHS.items()}
WD = {d: i for i, d in enumerate("monday tuesday wednesday thursday friday saturday sunday".split())}
MON = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
CUE = re.compile(r"\b(deadline|due|closes?\s+on|expires?\s+on|open through|no later than|rsvp|respond by|reply by|submit(?:ted)? by|must be (?:received|submitted|in)|"
                 r"by\s+(?:the\s+)?(?:end\s+of\s+(?:the\s+)?)?(?=\d|" + MON + r"\b|monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|today)|"
                 r"by\s+(?:close of business|cob|eod|end of (?:the )?day|noon|tomorrow|today|monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
                 r"\d{1,2}(?::\d{2})?\s?(?:am|pm)|" + MON + r"|\d{1,2}/\d{1,2})|"
                 r"before\s+(?:monday|tuesday|wednesday|thursday|friday|" + MON + r"|\d{1,2}/\d{1,2})|"
                 r"until\s+(?:monday|tuesday|wednesday|thursday|friday|" + MON + r"))\b", re.I)
def _mnum(w):
    w = w.lower(); return 9 if w.startswith("sept") else MABBR[w[:3]]
def _yr(y, mo, d, ref):
    if y is None:
        for cand in (ref.year, ref.year + 1, ref.year - 1):
            try: c = date(cand, mo, d)
            except ValueError: return None
            if timedelta(days=-3) <= c - ref <= timedelta(days=330): return c
        return None
    if y < 100: y += 1900 if y > 50 else 2000
    try: return date(y, mo, d)
    except ValueError: return None
def dates_in(s, ref):
    out, taken = [], []
    def add(a, b, dt, kind, txt=None):
        for (x, y) in taken:
            if a < y and b > x: return
        taken.append((a, b)); out.append((dt, txt or s[a:b], kind))
    for m in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", s):
        add(m.start(), m.end(), _yr(int(m[1]), int(m[2]), int(m[3]), ref), "abs")
    for m in re.finditer(MON + r"\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?\b", s, re.I):
        add(m.start(), m.end(), _yr(int(m[3]) if m[3] else None, _mnum(m[1]), int(m[2]), ref), "abs")
    for m in re.finditer(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?" + MON + r"\.?(?:,?\s+(\d{4}))?\b", s, re.I):
        add(m.start(), m.end(), _yr(int(m[3]) if m[3] else None, _mnum(m[2]), int(m[1]), ref), "abs")
    for m in re.finditer(r"(?<![\d/])(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?(?![\d/])", s):
        mo, d = int(m[1]), int(m[2])
        if 1 <= mo <= 12 and 1 <= d <= 31:
            add(m.start(), m.end(), _yr(int(m[3]) if m[3] else None, mo, d, ref), "abs")
    abs_spans = list(taken)
    for m in re.finditer(r"\b(next|this|coming)?\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", s, re.I):
        if any(-1 <= a - m.end() <= 3 or -1 <= m.start() - b <= 3 for a, b in abs_spans): continue
        w = WD[m[2].lower()]; q = (m[1] or "").lower(); delta = (w - ref.weekday()) % 7
        if q == "next" or delta == 0: add(m.start(), m.end(), None, "amb", m[0].strip())
        else: add(m.start(), m.end(), ref + timedelta(days=delta), "rel", m[0].strip())
    for m in re.finditer(r"\b(?:by|on|before)\s+the\s+(\d{1,2})(?:st|nd|rd|th)\b(?!\s+(?:of\s+)?" + MON + ")", s, re.I):
        dd = int(m[1]); cand = None
        for k in range(0, 3):
            y, mo = ref.year + (ref.month - 1 + k) // 12, (ref.month - 1 + k) % 12 + 1
            try: c = date(y, mo, dd)
            except ValueError: continue
            if c >= ref: cand = c; break
        add(m.start(), m.end(), cand, "rel" if cand else "amb")
    for m in re.finditer(r"\b(tomorrow|today)\b", s, re.I):
        add(m.start(), m.end(), ref + timedelta(days=1 if m[1].lower() == "tomorrow" else 0), "rel")
    return out
def sentences(text): return [x.strip() for x in re.split(r"(?<=[.!?])\s+|\n+", text) if x.strip()]
def extract(subject, body, ref):
    cands = []
    for sn in sentences(subject + "\n" + body):
        if not CUE.search(sn): continue
        cands.append((sn, dates_in(sn, ref)))
    if not cands: return dict(due=None, quote="", reason="no deadline cue")
    ds_all = [(d, t, k, sn) for sn, ds in cands for (d, t, k) in ds]
    if any(k == "amb" or d is None for d, t, k, sn in ds_all): return dict(due=None, quote=ds_all[0][3], reason="ambiguous date expression")
    uniq = sorted({d for d, *_ in ds_all})
    if not uniq: return dict(due=None, quote="", reason="cue without date")
    if len(uniq) > 1: return dict(due=None, quote=ds_all[0][3], reason="several different dates")
    d, t, k, sn = ds_all[0]
    if d < ref - timedelta(days=1): return dict(due=None, quote=sn, reason="date in the past")
    return dict(due=d.isoformat(), quote=sn, reason="single dated deadline sentence")
