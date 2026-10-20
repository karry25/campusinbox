import json, llm_tasks as t
from run_eval_v2_common import SUT_MODEL
for f in ("enron_sample.json", "adversarial_set.json"):
    for m in json.load(open(f)):
        try: t.run(SUT_MODEL, t.SYSTEM_EXTRACT, m, "sut" if "enron" in f else "adv")
        except Exception as e: print("ERR", m["id"], str(e)[:100], flush=True)
print("done")
