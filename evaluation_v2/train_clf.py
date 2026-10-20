"""Trained candidate-date classifier (logistic regression on context features).
Every date mention in a mail (found with rules_v2.dates_in, anchored to the Date header) is a candidate; a candidate is positive if it equals the
silver gold date. TRAIN = dev split only. TEST = test split, scored once. Fixed hyperparameters (C=1.0, threshold 0.5), no tuning on test.
Usage: python3 train_clf.py  -> writes clf_results_test.json, clf_rows_test.json, clf_cv_all.json"""
import json, re, hashlib, random
from datetime import date
import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
import rules_v2
S = json.load(open("enron_sample_labelled.json"))
def gold(m):
    a, b = m["labels"]["A"], m["labels"]["B"]
    if a and b and a["due"] == b["due"] and a["ambiguous"] == b["ambiguous"]: return a["due"]
    return "SKIP"
mails = [dict(m, gold=gold(m)) for m in S]; mails = [m for m in mails if m["gold"] != "SKIP"]
TOK = re.compile(r"[a-z]+|\d+")
def cands(m):
    ref = date.fromisoformat(m["date"][:10]); text = m["subject"] + "\n" + m["body"][:3000]; out = []
    pos = 0; sents = rules_v2.sentences(text); n = len(sents)
    for si, sn in enumerate(sents):
        ds = rules_v2.dates_in(sn, ref)
        for (d, tx, kind) in ds:
            if d is None: continue
            i = sn.find(tx); left = TOK.findall(sn[max(0, i - 80):i].lower())[-8:]; right = TOK.findall(sn[i + len(tx):i + len(tx) + 60].lower())[:6]
            f = {"kind=" + kind: 1, "cue": 1 if rules_v2.CUE.search(sn) else 0, "in_subject": 1 if si == 0 else 0, "relpos": si / max(n, 1),
                 "ndates_sent": len(ds), "days_bucket=%d" % max(-3, min(30, (d - ref).days)) if abs((d - ref).days) < 31 else "days_far": 1,
                 "past": 1 if d < ref else 0, "quoted": 1 if sn.lstrip().startswith((">", "From:", "To:", "Sent:")) else 0}
            for j, w in enumerate(reversed(left)): f["L:" + w] = 1; f["L%d:" % min(j, 3) + w] = 1
            for w in right: f["R:" + w] = 1
            for w in TOK.findall(sn.lower())[:60]: f["S:" + w] = 0.5
            out.append((d.isoformat(), f))
    return out
def build(ms):
    X, y, mid, dt = [], [], [], []
    for m in ms:
        for d, f in cands(m): X.append(f); y.append(1 if d == m["gold"] else 0); mid.append(m["id"]); dt.append(d)
    return X, np.array(y), mid, dt
def fit(ms):
    X, y, _, _ = build(ms); dv = DictVectorizer(); A = dv.fit_transform(X)
    clf = LogisticRegression(C=1.0, max_iter=2000).fit(A, y); return dv, clf, int(y.sum()), len(y)
def predict(dv, clf, ms, thr=0.5):
    res = {}
    for m in ms:
        cs = cands(m); best = (None, 0.0); probs = {}
        if cs:
            p = clf.predict_proba(dv.transform([f for _, f in cs]))[:, 1]
            for (d, _), pp in zip(cs, p): probs[d] = max(probs.get(d, 0), float(pp))
            best = max(probs.items(), key=lambda kv: kv[1])
        res[m["id"]] = dict(top=best[0] if best[0] and best[1] >= thr else None, p=best[1], probs=probs)
    return res
if __name__ == "__main__":
    train = [m for m in mails if m["split"] == "dev"]; test = [m for m in mails if m["split"] == "test"]
    dv, clf, npos, nc = fit(train); print("train mails", len(train), "candidates", nc, "positive candidates", npos)
    pr = predict(dv, clf, test); json.dump({k: dict(top=v["top"], p=v["p"], probs=v["probs"]) for k, v in pr.items()}, open("clf_rows_test.json", "w"))
    # top weights (for the paper)
    names = np.array(dv.get_feature_names_out()); w = clf.coef_[0]; order = np.argsort(w)
    print("top +", list(names[order[-12:]][::-1])); print("top -", list(names[order[:8]]))
    # 5-fold CV over all agreed mails (supplementary): each mail is predicted by a model that never saw it
    rnd = random.Random(7); ids = [m["id"] for m in mails]; rnd.shuffle(ids); fold = {i: k % 5 for k, i in enumerate(ids)}
    cv = {}
    for k in range(5):
        tr = [m for m in mails if fold[m["id"]] != k]; te = [m for m in mails if fold[m["id"]] == k]
        dvk, ck, _, _ = fit(tr); cv.update(predict(dvk, ck, te))
    json.dump({k: dict(top=v["top"], p=v["p"], probs=v["probs"]) for k, v in cv.items()}, open("clf_cv_all.json", "w"))
    print("done")
