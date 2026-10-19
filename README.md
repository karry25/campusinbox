# CampusInbox

A small agentic-AI web app that reads college emails, pulls out deadlines with evidence, and helps a student review, approve and track them - without ever sending a mail on its own.

Mini project for the Agentic AI course.

**Kareena Jahagirdar | PRN 123B1B048 | Division A**

## What's inside

| Folder | Contents |
| --- | --- |
| `CampusInbox_MVP/` | The running app (Python stdlib server + HTML/JS front end). Start here. |
| `evaluation/` | The labelled 65-mail eval corpus, the generator and scorer scripts, raw results, and the figure sources. See `evaluation/EVAL_README.md` to reproduce every number. |
| `screenshots/` | Screenshots of the app in use. |
| `docs/` | The IEEE paper and the full project report (docx + pdf). |

## Run it

```bash
cd CampusInbox_MVP
python3 app.py
```

Then open http://127.0.0.1:8765 in a browser. No install, no API key - it runs fully offline on the bundled sample mails.

## Reproduce the results

```bash
cd evaluation
python3 gen_eval.py     # writes eval_set.json (65 labelled mails)
python3 run_eval.py     # scores CampusInbox and the naive baseline against it
```

Numbers from the run on 20 Oct 2026 (Python 3.10.12): precision 100%, recall 55.6%, F1 71.4%, 0 wrong decisions on the 65-mail set. The corpus is synthetic - no public labelled college-deadline email dataset exists - and the paper says so openly.
