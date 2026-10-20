"""Minimal LLM REST client (Groq OpenAI-compatible, Gemini) with an on-disk response cache. No keys in the cache.
Keys: GROQ_API_KEY / GROQ_KEY_FILE, GEMINI_API_KEY / GEMINI_KEY_FILE. Model names starting 'groq:' use Groq."""
import os, json, hashlib, time, urllib.request, urllib.error
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "llm_cache")
os.makedirs(CACHE, exist_ok=True)
def _key():
    if os.getenv("GEMINI_API_KEY"): return os.environ["GEMINI_API_KEY"]
    return open(os.environ["GEMINI_KEY_FILE"]).read().strip()
def _groq_call(model, system, user, temperature, cp, tag):
    key = os.environ.get("GROQ_API_KEY") or open(os.environ["GROQ_KEY_FILE"]).read().strip()
    body = {"model": model, "temperature": temperature, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if model.startswith("openai/gpt-oss"): body["reasoning_effort"] = "low"
    if model.startswith("qwen/"): body["reasoning_effort"] = "none"; body["max_tokens"] = 400
    last = None
    for attempt in range(400 if os.environ.get("WAIT_QUOTA") else 12):
        t0 = time.time()
        req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", data=json.dumps(body).encode(),
              headers={"Content-Type": "application/json", "Authorization": "Bearer " + key, "User-Agent": "campusinbox-eval/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r: data = json.loads(r.read())
            raw = data["choices"][0]["message"].get("content") or ""
            try: parsed = json.loads(raw)
            except Exception: parsed = None
            meta = dict(model="groq:" + model, latency_s=round(time.time() - t0, 2), tag=tag, usage=data.get("usage", {}), cached=False)
            json.dump(dict(parsed=parsed, raw=raw, meta=meta), open(cp, "w"))
            return parsed, raw, meta
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code} {e.read()[:200]!r}"
            if e.code in (429, 500, 503):
                ra = float(e.headers.get("retry-after", 8))
                if ra > 150 and not os.environ.get("WAIT_QUOTA"): raise RuntimeError("DAILY_QUOTA " + last)
                time.sleep(ra + 1); continue
            if e.code == 400 and attempt < 2: time.sleep(2); continue
            raise RuntimeError(last)
        except Exception as e:
            last = repr(e); time.sleep(3 * (attempt + 1))
    raise RuntimeError("Groq call failed: " + str(last))
def call(model, system, user, temperature=0.0, tag=""):
    ck = hashlib.sha256(json.dumps([model, system, user, temperature], sort_keys=True).encode()).hexdigest()
    cp = os.path.join(CACHE, ck + ".json")
    if os.path.exists(cp):
        d = json.load(open(cp)); return d["parsed"], d["raw"], dict(d["meta"], cached=True)
    if model.startswith("groq:"): return _groq_call(model[5:], system, user, temperature, cp, tag)
    body = {"systemInstruction": {"parts": [{"text": system}]}, "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": temperature, "responseMimeType": "application/json"}}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    last = None
    for attempt in range(2):
        t0 = time.time()
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": _key()})
        try:
            with urllib.request.urlopen(req, timeout=40) as r: data = json.loads(r.read())
            parts = data["candidates"][0]["content"]["parts"]
            raw = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            try: parsed = json.loads(raw)
            except Exception: parsed = None
            meta = dict(model=model, latency_s=round(time.time() - t0, 2), tag=tag, usage=data.get("usageMetadata", {}), cached=False)
            json.dump(dict(parsed=parsed, raw=raw, meta=meta), open(cp, "w")); return parsed, raw, meta
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code} {e.read()[:200]!r}"
            if e.code in (429, 500, 503, 504): time.sleep(5 * (attempt + 1)); continue
            raise RuntimeError(last)
        except Exception as e: last = repr(e); time.sleep(3)
    raise RuntimeError("Gemini call failed: " + str(last))
