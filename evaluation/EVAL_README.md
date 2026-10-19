# CampusInbox evaluation bundle
Kareena Jahagirdar | PRN 123B1B048 | Division A

Reproduce the numbers in the paper and report:

1. cd CampusInbox_MVP && python3 -m unittest -v     (23 tests)
2. python3 demo_walkthrough.py                       (8 HTTP checks)
3. cd ../evaluation && python3 gen_eval.py           (writes eval_set.json, 65 synthetic mails)
4. cp ../CampusInbox_MVP/app.py . && python3 run_eval.py   (writes eval_results.json + per-mail rows)

The corpus is synthetic and author-labelled by design; every mail carries a ground-truth
deadline (or none) in its _gt_due field. The naive baseline is implemented inside run_eval.py.
Measured on 20 Oct 2026, Python 3.10.12: rules precision 100%, recall 55.6%, F1 71.4%,
decision safety 100% (0 wrong of 65); naive baseline precision 50.0%, decision safety 60.0%.
