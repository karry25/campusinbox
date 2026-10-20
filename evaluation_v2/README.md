# CampusInbox evaluation v2 (public Enron mail)
Labels are SILVER: two open-weight LLMs (Groq: gpt-oss-120b, qwen3.8-27b) labelled each mail; only mails where both agree are in the reference. System under test: gpt-oss-20b. Live demo: Gemini gemini-3.1-flash-lite (synthetic mails only). No human annotated the main reference; see human_results.json if present for a small human spot check.
Reproduce scoring without any API (all model responses are cached in llm_cache/):
  python3 collect_labels.py && python3 run_eval_v2.py dev && python3 run_eval_v2.py test && python3 run_adv.py
Fresh run needs GROQ_KEY_FILE (and the CMU Enron tarball for build_enron.py; seed 20261020). rules_v2.py is frozen; do not tune on the test split.
Human check: make_adjudication.py builds the sheet and adjudication_key.json; score_human.py answers.txt scores it.
Files: results_dev.json, results_test.json, results_adversarial.json, rows_*.json (per-mail outputs), live_demo.py + live_demo_log.json.
