"""Draw the evaluation sample from the Enron pool (seed 20261020), split dev/test, and warm the label cache.
ONLY=A|B restricts to one labeller. Labelling responses are cached in llm_cache/ (pushed with the repo)."""
import json, random, hashlib, os
from concurrent.futures import ThreadPoolExecutor
import llm_tasks as t
if os.path.exists("enron_sample.json"):
    sample = json.load(open("enron_sample.json"))   # frozen sample, drawn once with seed 20261020 by the code below on first run
else:
    pool = json.load(open("enron_pool.json"))
    rnd = random.Random(20261020)
    cue = sorted(pool["cue_pool"], key=lambda m: m["id"]); nocue = sorted(pool["nocue_pool"], key=lambda m: m["id"])
    rnd.shuffle(cue); rnd.shuffle(nocue)
    sample = [dict(m, stratum="cue") for m in cue[:200]] + [dict(m, stratum="nocue") for m in nocue[:100]]
    for m in sample: m["split"] = "dev" if int(hashlib.md5(m["id"].encode()).hexdigest(), 16) % 10 < 3 else "test"
    json.dump(sample, open("enron_sample.json", "w"), indent=1)
ALL_LAB = [("A", "groq:openai/gpt-oss-120b", t.SYSTEM_LABEL_A), ("B", "groq:qwen/qwen3.8-27b", t.SYSTEM_LABEL_B)]
ONLY = os.environ.get("ONLY"); LAB = [l for l in ALL_LAB if (not ONLY or l[0] == ONLY)]
def job(args):
    m, (name, model, sysmsg) = args
    try: t.run(model, sysmsg, m, "label" + name)
    except Exception as e: print("ERR", name, m["id"], str(e)[:150], flush=True)
with ThreadPoolExecutor(1) as ex: list(ex.map(job, [(m, l) for m in sample for l in LAB]))
print("warmed cache for", ONLY or "A+B")
