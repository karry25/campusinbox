"""Evaluate all systems on the labelled Enron sample (dev for development, test for reporting).
Gold = both LLM labellers agree, overridden by human adjudications.json ({id: {"due": "YYYY-MM-DD"|null}}) when present.
Usage: python3 run_eval_v2.py [dev|test|all]"""
import json, sys, os, random
from datetime import date
import rules_v2, llm_tasks as t
from run_eval_v2_common import SUT_MODEL
split = sys.argv[1] if len(sys.argv) > 1 else "test"
sample = [m for m in json.load(open("enron_sample_labelled.json")) if split == "all" or m["split"] == split]
adj = json.load(open("adjudications.json")) if os.path.exists("adjudications.json") else {}
def gold(m):
    if m["id"] in adj: return ("human", adj[m["id"]]["due"], False)
    a, b = m["labels"]["A"], m["labels"]["B"]
    if not a or not b: return ("pending", None, None)
    if a["due"] == b["due"] and a["ambiguous"] == b["ambiguous"]: return ("silver", a["due"], a["ambiguous"])
    return ("disputed", None, None)
def naive(m):
    ref = date.fromisoformat(m["date"][:10]); ds = [d for d, tx, k in rules_v2.dates_in(m["subject"] + "\n" + m["body"], ref) if d]
    return ds[0].isoformat() if ds else None
rows = []
for m in sample:
    src, gd, gamb = gold(m)
    if src in ("disputed", "pending"): continue
    l = t.run(SUT_MODEL, t.SYSTEM_EXTRACT, m, "sut")
    import gem
    parsed, _, _ = gem.call(SUT_MODEL, t.SYSTEM_EXTRACT, t.user_msg(m), 0.0, "sut")
    raw = parsed.get("deadline_date") if isinstance(parsed, dict) and parsed.get("has_deadline") else None
    r2 = rules_v2.extract(m["subject"], m["body"], date.fromisoformat(m["date"][:10]))
    gate = r2["due"] if (r2["due"] and l["due"] == r2["due"]) else None
    rows.append(dict(id=m["id"], gold_src=src, gold=gd, gold_ambiguous=gamb, stratum=m["stratum"], naive=naive(m), rules_v2=r2["due"],
                     llm_raw=raw, llm_verified=l["due"], hybrid_auto=gate, llm_lat=l.get("latency_s"), llm_tok=l.get("tokens"),
                     review_needed=bool((r2["due"] or l["due"]) and not gate)))
SYS = ["naive", "rules_v2", "llm_raw", "llm_verified", "hybrid_auto"]
def score(rs, s):
    emit = [r for r in rs if r[s]]; pos = [r for r in rs if r["gold"]]; tp = [r for r in emit if r[s] == r["gold"]]
    p = len(tp) / len(emit) if emit else float("nan"); rc = len(tp) / len(pos) if pos else float("nan")
    f1 = 2 * p * rc / (p + rc) if emit and tp else 0.0
    return dict(n=len(rs), emitted=len(emit), correct=len(tp), wrong=len(emit) - len(tp), precision=p, recall=rc, f1=f1, wrong_rate=(len(emit) - len(tp)) / len(rs))
def boot(rs, s, key, B=2000, seed=1):
    rnd = random.Random(seed); v = []
    for _ in range(B):
        x = score([rnd.choice(rs) for _ in rs], s)[key]
        if x == x: v.append(x)
    v.sort(); return [round(v[int(.025 * len(v))], 4), round(v[int(.975 * len(v)) - 1], 4)] if v else None
out = dict(split=split, n=len(rows), gold_sources={k: sum(1 for r in rows if r["gold_src"] == k) for k in ("silver", "human")}, positives=sum(1 for r in rows if r["gold"]), systems={})
for s in SYS:
    sc = score(rows, s); sc.update({k + "_ci95": boot(rows, s, k) for k in ("precision", "recall", "f1")}); out["systems"][s] = sc
out["review_rate_hybrid"] = sum(r["review_needed"] for r in rows) / len(rows)
json.dump(out, open(f"results_{split}.json", "w"), indent=1); json.dump(rows, open(f"rows_{split}.json", "w"), indent=1)
for s in SYS:
    x = out["systems"][s]; print(f"{s:13s} emit={x['emitted']:3d} P={x['precision']:.3f} R={x['recall']:.3f} F1={x['f1']:.3f} wrong={x['wrong']}")
print(out["n"], out["gold_sources"], "positives", out["positives"], "review_rate", round(out["review_rate_hybrid"], 3))
