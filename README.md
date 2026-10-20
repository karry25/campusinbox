# CampusInbox - evidence-gated deadline assistant for college mail

CampusInbox turns deadline mails into **reviewed** deadlines, reminders, calendar entries and draft replies to faculty. Rule: *evidence before action*. A date is only a proposal until a person approves it, every proposal carries the sentence it came from, and the app has no send-mail capability.

Author: Kareena Jahagirdar, PCCOE Pune (PRN 123B1B048, Div A). Course: Agentic AI Design.

## What is in this repo
| Path | Content |
|---|---|
| `CampusInbox_MVP/` | The app (stdlib-only Python 3.10, SQLite, plain web UI), 25 unit tests, `rules_v2.py` (frozen rule engine) |
| `evaluation_v2/` | Evaluation on public Enron mail: sampling, labelling, scoring, injection test, cached model responses, results JSON |
| `docs/` | Final paper (docx + pdf), figures, diagram sources (`*.dot`), paper build script |
| `screenshots/` | Screenshots of the running app, including a live run with Gemini |

## Quick start (app)
```
cd CampusInbox_MVP && python3 app.py          # opens on http://127.0.0.1:8765, offline rules mode
python3 -m unittest -v                         # 25 tests
```
Optional model mode (any OpenAI-compatible endpoint): set `CAMPUS_MODEL_URL`, `CAMPUS_MODEL_NAME`, `CAMPUS_MODEL_KEY`. The model may only *suggest*: its quote must occur in the mail, rule and model dates are compared, and a human approves every date. **Do not put your key in the repo.**

## Results summary (test split, 178 Enron mails, 93 positives; labels are SILVER)
| System | Precision | Recall | Review rate |
|---|---|---|---|
| Naive first date | 37.3 | 60.2 | - |
| Rules (frozen) | 84.7 | 65.6 | - |
| Prompted LLM (gpt-oss-20b) + quote check | 91.8 | 95.7 | - |
| Rules and LLM must agree | 98.3 | 63.4 | 24.2% |

Injection test (40 synthetic mails): an injected "the real deadline is X" was accepted 20/40 (rules), 23/40 (LLM), 12/40 (agreement gate). **This is a negative result**: the gate guards against invented dates, not against a hostile sender. See the paper for intervals, ablations and error analysis.

## Reproduce the numbers (no API needed, all model responses are cached)
```
cd evaluation_v2
python3 collect_labels.py
python3 run_eval_v2.py dev && python3 run_eval_v2.py test
python3 run_adv.py
```
Re-running the language models needs your own API keys (Groq for labelling and the system under test, Google for the live demo), passed through key files named in `gem.py`/`live_demo.py`. `build_enron.py` rebuilds the pool from the public CMU Enron tarball (seed 20261020).

## Honest limits
- Labels come from **two AI models** (gpt-oss-120b, qwen3.8-27b on Groq's free tier); only mails where both agree are used (237 of 261). No independent human labelled this data. A 50-mail subset (`evaluation_v2/ai_proposals.json`) was proposed by an AI assistant and reported as reviewed by the author without changes; it is not independent human labelling.
- The language models are **prompted, not trained** by us. No model was trained in this work.
- Enron is corporate mail from 1999-2002, not student mail; the test split is small, intervals are wide.
- Rules were tuned on the dev split; the test split was scored after the rules were frozen. One quote-matching bug (hard-wrapped lines) was fixed after a first scoring run.
- No user study. Real student mail was never sent to any model API.

## License note
Code: no license has been chosen yet; add one (for example MIT) before others reuse it. The Enron corpus is public (CMU) and is not redistributed in full here; only the 300-mail sample and labels used in the paper are included.
