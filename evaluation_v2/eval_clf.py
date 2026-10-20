"""Score the trained classifier and trained-verifier hybrids. Run train_clf.py first. Writes results_clf.json"""
import json, random, sys
sys.argv = [sys.argv[0]]
rows_t = json.load(open("rows_test.json")); rows_d = json.load(open("rows_dev.json"))
CT = json.load(open("clf_rows_test.json")); CV = json.load(open("clf_cv_all.json"))
def score(rs, s):
    emit = [r for r in rs if r[s]]; pos = [r for r in rs if r["gold"]]; tp = [r for r in emit if r[s] == r["gold"]]
    p = len(tp) / len(emit) if emit else float("nan"); rc = len(tp) / len(pos) if pos else float("nan")
    f1 = 2 * p * rc / (p + rc) if emit and tp else 0.0
    return dict(n=len(rs), emitted=len(emit), correct=len(tp), wrong=len(emit) - len(tp), precision=p, recall=rc, f1=f1)
def boot(rs, s, key, B=2000, seed=1):
    rnd = random.Random(seed); v = []
    for _ in range(B):
        x = score([rnd.choice(rs) for _ in rs], s)[key]
        if x == x: v.append(x)
    v.sort(); return [round(v[int(.025 * len(v))], 4), round(v[int(.975 * len(v)) - 1], 4)]
def add(rows, C):
    for r in rows:
        c = C[r["id"]]; top = c["top"]; l = r["llm_verified"]; ru = r["rules_v2"]
        r["clf"] = top
        r["llm_clf_verified"] = l if (l and c["probs"].get(l, 0) >= 0.5) else None      # trained model as verifier of the LLM date
        r["llm_clf_agree"] = l if (l and l == top) else None                               # LLM date == trained top candidate
        r["rules_clf_agree"] = ru if (ru and ru == top) else None
        votes = [x for x in (ru, l, top) if x]; r["vote2of3"] = next((v for v in set(votes) if votes.count(v) >= 2), None)
        r["any_emitted"] = bool(ru or l or top)
        r["review_clf_gate"] = bool((l or top) and not r["llm_clf_agree"]); r["review_vote"] = bool(r["any_emitted"] and not r["vote2of3"])
SYS = ["rules_v2", "llm_verified", "hybrid_auto", "clf", "llm_clf_verified", "llm_clf_agree", "rules_clf_agree", "vote2of3"]
out = {}
for name, rows, C in (("test_trained_on_dev", rows_t, CT), ("cv5_all_agreed", rows_d + rows_t, CV)):
    add(rows, C); o = dict(n=len(rows), positives=sum(1 for r in rows if r["gold"]), systems={})
    for s in SYS:
        sc = score(rows, s); sc.update({k + "_ci95": boot(rows, s, k) for k in ("precision", "recall", "f1")}); o["systems"][s] = sc
    o["review_rate_clf_gate"] = sum(r["review_clf_gate"] for r in rows) / len(rows); o["review_rate_vote"] = sum(r["review_vote"] for r in rows) / len(rows)
    o["review_rate_hybrid"] = sum(r["review_needed"] for r in rows) / len(rows)
    out[name] = o; print(name, o["n"], o["positives"], "review: clfgate %.3f vote %.3f rules-llm %.3f" % (o["review_rate_clf_gate"], o["review_rate_vote"], o["review_rate_hybrid"]))
    for s in SYS:
        x = o["systems"][s]; print(f"  {s:17s} emit={x['emitted']:3d} ok={x['correct']:3d} P={x['precision']:.3f} R={x['recall']:.3f} F1={x['f1']:.3f} P-ci={x['precision_ci95']} R-ci={x['recall_ci95']}")
    if name.startswith("test"): json.dump(rows, open("rows_test_with_clf.json", "w"))
json.dump(out, open("results_clf.json", "w"), indent=1)
