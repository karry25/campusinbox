import json, re, os, sys, time
os.environ.pop('CAMPUS_MODEL_URL', None)
import importlib.util
spec = importlib.util.spec_from_file_location("campusapp", "app.py")
app = importlib.util.module_from_spec(spec); spec.loader.exec_module(app)

mails = json.load(open("eval_set.json"))

def norm(s):
    if not s: return None
    from datetime import datetime
    return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone().isoformat()

def naive_baseline(body):
    """Naive first-date baseline: grabs the first date-like string it can parse, guesses otherwise."""
    # ISO datetime
    x = re.search(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:[+-]\d{2}:?\d{2}|Z)?', body)
    if x:
        s = x.group(0).replace(' ', 'T')
        try:
            from datetime import datetime
            s2 = s if re.search(r'([+-]\d{2}:?\d{2}|Z)$', s) else s + '+05:30'
            s2 = re.sub(r'([+-]\d{2})(\d{2})$', r'\1:\2', s2)
            return datetime.fromisoformat(s2.replace('Z','+00:30') if s2.endswith('Z') else s2).isoformat()
        except Exception: pass
    # 24 October 2026 / 24 Oct 2026 / October 26, 2026
    months = {m.lower(): k+1 for k, m in enumerate(['January','February','March','April','May','June','July','August','September','October','November','December'])}
    x = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})', body)
    if x and x.group(2).lower()[:3] in {k[:3] for k in months}:
        mon = [v for k, v in months.items() if k[:3] == x.group(2).lower()[:3]][0]
        return f"{x.group(3)}-{mon:02d}-{int(x.group(1)):02d}T00:00:00+05:30"
    x = re.search(r'([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})', body)
    if x and x.group(1).lower()[:3] in {k[:3] for k in months}:
        mon = [v for k, v in months.items() if k[:3] == x.group(1).lower()[:3]][0]
        return f"{x.group(3)}-{mon:02d}-{int(x.group(2)):02d}T00:00:00+05:30"
    # dd/mm/yyyy or dd-mm-yyyy or dd.mm.yyyy
    x = re.search(r'\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b', body)
    if x:
        return f"{x.group(3)}-{int(x.group(2)):02d}-{int(x.group(1)):02d}T00:00:00+05:30"
    # relative words: baseline "guesses" a date (naive behaviour)
    if re.search(r'next Friday', body, re.I): return "2026-10-23T17:00:00+05:30"
    if re.search(r'tomorrow', body, re.I): return "2026-10-21T17:00:00+05:30"
    if re.search(r'next Monday', body, re.I): return "2026-10-26T09:00:00+05:30"
    if re.search(r'next week', body, re.I): return "2026-10-26T17:00:00+05:30"
    if re.search(r'two days', body, re.I): return "2026-10-22T17:00:00+05:30"
    if re.search(r'end of this week', body, re.I): return "2026-10-25T17:00:00+05:30"
    if re.search(r'next lecture', body, re.I): return "2026-10-21T09:00:00+05:30"
    if re.search(r'Diwali', body, re.I): return "2026-11-08T17:00:00+05:30"
    return None

def run(engine_fn, label):
    rows = []
    t0 = time.perf_counter()
    for mail in mails:
        body = mail['body']
        gt = mail['_gt_due']
        err = None
        try:
            if engine_fn == 'app':
                out = app.EvidenceExtractor.extract(mail)
                pred = out['due_at']; course = out['course']; title = out['title']
            else:
                pred = naive_baseline(body); course = None; title = None
        except Exception as e:
            pred, course, title, err = None, None, None, str(e)
        rows.append(dict(id=mail['id'], cat=mail['_cat'], gt=gt, pred=pred, err=err,
                         correct_date=(norm(pred) == norm(gt) if (pred and gt) else False),
                         course=course, gt_course=mail['_gt_course'], title=title, gt_task=mail['_gt_task']))
    dt = (time.perf_counter() - t0) * 1000
    n = len(rows)
    extracted = [r for r in rows if r['pred']]
    has_due = [r for r in rows if r['gt']]
    no_due = [r for r in rows if not r['gt']]
    tp = [r for r in extracted if r['correct_date']]
    wrong = [r for r in extracted if not r['correct_date']]
    false_on_nodue = [r for r in no_due if r['pred']]
    precision = len(tp)/len(extracted) if extracted else 0
    recall = len(tp)/len(has_due)
    f1 = 2*precision*recall/(precision+recall) if precision+recall else 0
    # decision safety: wrong auto-extracted dates (any category)
    safety = 1 - len(wrong)/n
    # routing accuracy: correct handling overall = correct date extracted, or correctly abstained on no-deadline mail
    routed = len(tp) + len([r for r in no_due if not r['pred']])
    # abstention on ambiguous+nodue
    amb = [r for r in rows if r['cat'] in ('C_ambiguous','D_no_deadline')]
    abstained = [r for r in amb if not r['pred']]
    res = dict(engine=label, n=n, ms_total=round(dt,1), ms_per_mail=round(dt/n,2),
               extracted=len(extracted), correct=len(tp), wrong=len(wrong),
               precision=round(precision,4), recall=round(recall,4), f1=round(f1,4),
               decision_safety=round(safety,4), routing_accuracy=round(routed/n,4),
               false_on_no_deadline=len(false_on_nodue),
               abstain_on_ambiguous=f"{len(abstained)}/{len(amb)}")
    # per category
    cats = {}
    for c in sorted({r['cat'] for r in rows}):
        rr = [r for r in rows if r['cat'] == c]
        ce = [r for r in rr if r['pred']]; ct = [r for r in rr if r['correct_date']]
        cats[c] = dict(n=len(rr), extracted=len(ce), correct=len(ct), wrong=len(ce)-len(ct))
    res['by_category'] = cats
    return res, rows

res_app, rows_app = run('app', 'CampusInbox offline rules')
res_nb, rows_nb = run('naive', 'Naive first-date baseline')
out = dict(app=res_app, naive=res_nb)
json.dump(out, open('eval_results.json','w'), indent=1)
json.dump(rows_app, open('eval_rows_app.json','w'), indent=1)
json.dump(rows_nb, open('eval_rows_naive.json','w'), indent=1)
for r in (res_app, res_nb):
    print(json.dumps({k:v for k,v in r.items() if k!='by_category'}, indent=1))
    print(' by category:', json.dumps(r['by_category']))
# field accuracy for app on structured mails
fa = [r for r in rows_app if r['cat']=='A_structured']
print('course field acc (A):', sum(1 for r in fa if r['course']==r['gt_course']),'/',len(fa))
print('task field acc (A):', sum(1 for r in fa if r['title']==r['gt_task']),'/',len(fa))
# errors
print('app errors:', [ (r['id'], r['err']) for r in rows_app if r['err'] ][:5])
