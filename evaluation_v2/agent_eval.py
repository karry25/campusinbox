"""Evaluate the agent layer on the labelled Enron split with the same scorer as run_eval_v2.py.
Usage: GROQ_KEY_FILE=... python3 agent_eval.py dev|test [limit]
Systems: scripted_agent (offline, no model), react_agent (prompted gpt-oss-20b picks tools), react_agree (react date equals rules date),
llm_plus_verifier (existing LLM+quote-check proposal, then a Verifier role)."""
import json, sys, os, time, hashlib, urllib.request, urllib.error
from datetime import date
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "../CampusInbox_MVP")
import agent_loop, rules_v2
PROVIDER = os.environ.get("PROVIDER", "groq")
MODEL = "gemini-3.1-flash-lite" if PROVIDER == "gemini" else "openai/gpt-oss-20b"
URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions" if PROVIDER == "gemini" else "https://api.groq.com/openai/v1/chat/completions"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "llm_cache_agent" + ("_gemini" if PROVIDER == "gemini" else "")); os.makedirs(CACHE, exist_ok=True)
def chat(messages, tools=None):
    """Returns the assistant message dict (content, tool_calls). Responses are cached on disk (no keys)."""
    ck = hashlib.sha256(json.dumps([MODEL, messages, bool(tools)], sort_keys=True).encode()).hexdigest(); cp = os.path.join(CACHE, ck + ".json")
    if os.path.exists(cp): return json.load(open(cp))["message"]
    key = open(os.environ["GROQ_KEY_FILE"]).read().strip()
    body = {"model": MODEL, "temperature": 0, "messages": messages}
    if PROVIDER != "gemini": body["reasoning_effort"] = "low"
    if tools: body["tools"] = tools; body["tool_choice"] = "auto"
    else: body["response_format"] = {"type": "json_object"}
    for attempt in range(40):
        req = urllib.request.Request(URL, data=json.dumps(body).encode(),
              headers={"Content-Type": "application/json", "Authorization": "Bearer " + key, "User-Agent": "campusinbox-eval/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r: data = json.loads(r.read())
            m = data["choices"][0]["message"]; msg = {"content": m.get("content") or "", "tool_calls": m.get("tool_calls") or []}
            json.dump(dict(message=msg, usage=data.get("usage", {})), open(cp, "w")); return msg
        except urllib.error.HTTPError as e:
            raw = e.read()
            if e.code in (429, 500, 503):
                ra = float(e.headers.get("retry-after", 6))
                if ra > 300: raise RuntimeError("DAILY_QUOTA " + repr(raw[:200]))
                time.sleep(ra + 1); continue
            if e.code == 400 and b"tool_use_failed" in raw:
                # malformed function call from the model: keep what it clearly meant, otherwise return no call (the loop nudges once)
                msg = {"content": "", "tool_calls": []}
                try:
                    fg = json.loads(json.loads(raw)["error"]["failed_generation"]); nm = fg.get("name"); ar = fg.get("arguments") or {}
                    if nm == "json": nm = "final_answer"
                    if nm in [t["function"]["name"] for t in (tools or [])]:
                        msg["tool_calls"] = [{"id": "m1", "function": {"name": nm, "arguments": json.dumps(ar)}}]
                except Exception: pass
                json.dump(dict(message=msg, usage={}, malformed_call=True), open(cp, "w")); return msg
            if e.code == 400 and attempt < 2: time.sleep(2); continue
            raise RuntimeError("HTTP %s %r" % (e.code, raw[:300]))
        except Exception: time.sleep(3)
    raise RuntimeError("chat failed")
split = sys.argv[1]; limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
base = {r["id"]: r for r in json.load(open(f"rows_{split}.json"))}
mails = {m["id"]: m for m in json.load(open("enron_sample_labelled.json"))}
ids = list(base)[:limit]
def work(i):
    m = mails[i]; ref = date.fromisoformat(m["date"][:10]); b = base[i]
    sc = agent_loop.run_scripted(m["subject"], m["body"], ref)
    ag = agent_loop.run_agent(chat, m["subject"], m["body"], ref)
    ver = None
    if b["llm_verified"]:
        tools = agent_loop.MailTools(m["subject"], m["body"], ref)
        import llm_tasks as t, gem
        parsed, _, _ = gem.call("groq:openai/gpt-oss-20b", t.SYSTEM_EXTRACT, t.user_msg(m), 0.0, "sut")
        q = (parsed or {}).get("quote", "")
        ver = agent_loop.verify(chat, tools, b["llm_verified"], q)
    return dict(id=i, gold=b["gold"], rules_v2=b["rules_v2"], llm_verified=b["llm_verified"], scripted_agent=sc["due"],
                react_agent=ag["due"], react_agree=ag["due"] if ag["due"] and ag["due"] == b["rules_v2"] else None,
                llm_plus_verifier=b["llm_verified"] if ver and ver["verdict"] == "accept" else None,
                steps=ag["steps"], react_note=ag["note"], ver_verdict=ver["verdict"] if ver else None, trace=ag["trace"], ver_msgs=ver["messages"] if ver else None)
import random as _r
budget = float(os.environ.get("BUDGET_S", "0")) or None
if os.environ.get("SHUFFLE_SEED"): _r.Random(int(os.environ["SHUFFLE_SEED"])).shuffle(ids)  # fixed seed: the subset that finishes is a random sample
rows, t0 = [], time.time()
with ThreadPoolExecutor(12) as ex:
    for k in range(0, len(ids), 12):
        if budget and time.time() - t0 > budget: break
        rows += list(ex.map(work, ids[k:k + 12]))
        json.dump(rows, open(f"rows_agent_{PROVIDER}_{split}.json", "w"))
print("completed", len(rows), "of", len(ids), "mails")
json.dump(rows, open(f"rows_agent_{PROVIDER}_{split}.json", "w"), indent=1)
import random
def score(rs, s):
    emit = [r for r in rs if r[s]]; pos = [r for r in rs if r["gold"]]; tp = [r for r in emit if r[s] == r["gold"]]
    p = len(tp) / len(emit) if emit else float("nan"); rc = len(tp) / len(pos) if pos else float("nan")
    return dict(n=len(rs), emitted=len(emit), correct=len(tp), wrong=len(emit) - len(tp), precision=p, recall=rc, f1=(2*p*rc/(p+rc) if emit and tp else 0.0))
def boot(rs, s, key, B=2000, seed=1):
    rnd = random.Random(seed); v = []
    for _ in range(B):
        x = score([rnd.choice(rs) for _ in rs], s)[key]
        if x == x: v.append(x)
    v.sort(); return [round(v[int(.025*len(v))], 4), round(v[int(.975*len(v))-1], 4)] if v else None
out = dict(split=split, n=len(rows), positives=sum(1 for r in rows if r["gold"]), mean_steps=round(sum(r["steps"] for r in rows)/len(rows), 2), systems={})
for s in ("rules_v2", "llm_verified", "scripted_agent", "react_agent", "react_agree", "llm_plus_verifier"):
    sc = score(rows, s); sc.update({k + "_ci95": boot(rows, s, k) for k in ("precision", "recall", "f1")}); out["systems"][s] = sc
json.dump(out, open(f"results_agent_{PROVIDER}_{split}.json", "w"), indent=1)
for s, x in out["systems"].items(): print(f"{s:18s} emit={x['emitted']:3d} P={x['precision']:.3f} R={x['recall']:.3f} F1={x['f1']:.3f} wrong={x['wrong']}")
print(out["n"], "positives", out["positives"], "mean steps", out["mean_steps"])
