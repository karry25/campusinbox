"""Build enron_sample_labelled.json from the response cache only (no API calls). Missing label = pending."""
import json, hashlib, os
import llm_tasks as t, gem
sample = json.load(open("enron_sample.json"))
LAB = [("A", "groq:openai/gpt-oss-120b", t.SYSTEM_LABEL_A), ("B", "groq:qwen/qwen3.8-27b", t.SYSTEM_LABEL_B)]
def cached(model, system, m):
    ck = hashlib.sha256(json.dumps([model, system, t.user_msg(m), 0.0], sort_keys=True).encode()).hexdigest()
    p = os.path.join(gem.CACHE, ck + ".json")
    if not os.path.exists(p): return None
    d = json.load(open(p)); r = t.normalise(d["parsed"], m, lenient=True); r["latency_s"] = d["meta"].get("latency_s"); return r
for m in sample: m["labels"] = {n: cached(mod, sy, m) for n, mod, sy in LAB}
json.dump(sample, open("enron_sample_labelled.json", "w"), indent=1)
a = sum(1 for m in sample if m["labels"]["A"]); b = sum(1 for m in sample if m["labels"]["B"])
both = [m for m in sample if m["labels"]["A"] and m["labels"]["B"]]
ag = sum(1 for m in both if m["labels"]["A"]["due"] == m["labels"]["B"]["due"] and m["labels"]["A"]["ambiguous"] == m["labels"]["B"]["ambiguous"])
print(f"n={len(sample)} labelledA={a} labelledB={b} both={len(both)} agree={ag}")
