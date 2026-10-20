"""Score Kareena's answers to the label check sheet. Usage: python3 score_human.py answers.txt  -> human_results.json
Answers like: '1 D 2001-05-09, 2 N, 3 X, 4 ?'. Uses adjudication_key.json (A/B labels hidden from the rater)."""
import re, json, sys
key = {k['n']: k for k in json.load(open('adjudication_key.json'))}
txt = open(sys.argv[1]).read()
ans = {}
for m in re.finditer(r'(\d+)\s*[.:)-]?\s*(D\s*\d{4}-\d{2}-\d{2}|N|X|\?)', txt, re.I):
    n = int(m.group(1)); v = re.sub(r'\s+', ' ', m.group(2).upper()); 
    if n in key and n not in ans: ans[n] = v
def lab(due, amb): return 'X' if amb else ('N' if due is None else 'D ' + due)
out = {'answered': 0, 'skipped_unclear': 0, 'human_X': 0, 'A_right': 0, 'B_right': 0, 'both_right': 0, 'items': []}
agr = {'n': 0, 'silver_right': 0}; dis = {'n': 0, 'A_right': 0, 'B_right': 0, 'neither': 0}
for n, v in sorted(ans.items()):
    k = key[n]
    if v == '?': out['skipped_unclear'] += 1; continue
    if v == 'X': out['human_X'] += 1; continue
    out['answered'] += 1
    a, b = lab(k['A'], k['A_amb']), lab(k['B'], k['B_amb']); ar, br = a == v, b == v
    out['A_right'] += ar; out['B_right'] += br; out['both_right'] += ar and br
    if k['kind'] == 'check':
        agr['n'] += 1; agr['silver_right'] += ar and br
    else:
        dis['n'] += 1; dis['A_right'] += ar; dis['B_right'] += br; dis['neither'] += (not ar and not br)
    out['items'].append(dict(n=n, id=k['id'], kind=k['kind'], human=v, A=a, B=b))
out['agreed_subset'] = agr; out['dispute_subset'] = dis
json.dump(out, open('human_results.json', 'w'), indent=1); print(json.dumps({k: v for k, v in out.items() if k != 'items'}, indent=1))
