import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patches as mp

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':7.5,'text.color':'black'})

def box(ax, x, y, w, h, text, fs=7.5, bold=False, ls='-'):
    ax.add_patch(FancyBboxPatch((x,y), w, h, boxstyle="round,pad=0.012", fc='white', ec='black', lw=0.9, ls=ls))
    ax.text(x+w/2, y+h/2, text, ha='center', va='center', fontsize=fs, fontweight='bold' if bold else 'normal')

def arrow(ax, x1, y1, x2, y2, label=None, dashed=False, lx=0, ly=0.03):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2), arrowstyle='-|>', mutation_scale=9, lw=0.9, color='black', linestyle='--' if dashed else '-'))
    if label:
        ax.text((x1+x2)/2+lx, (y1+y2)/2+ly, label, fontsize=6.3, ha='center')

# ---------- Fig 1: architecture ----------
fig, ax = plt.subplots(figsize=(3.45, 4.6)); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis('off')
box(ax, 0.02, 0.905, 0.44, 0.075, 'Mail sources\n(import / .eml / JSON)')
box(ax, 0.54, 0.905, 0.44, 0.075, 'Sample Classroom status\n(synthetic fixture)')
box(ax, 0.28, 0.78, 0.44, 0.07, 'Import + validation layer\n(atomic batch, dedup, size limits)')
box(ax, 0.05, 0.63, 0.40, 0.085, 'Role 1: EvidenceExtractor\nproposes deadline +\nverbatim source quote', bold=True)
box(ax, 0.55, 0.63, 0.40, 0.085, 'Optional model adapter\n(OpenAI-compatible,\nquote-checked)')
box(ax, 0.28, 0.50, 0.44, 0.075, 'Human review gate\n(no auto-approval)')
box(ax, 0.28, 0.385, 0.44, 0.07, 'Task store (SQLite)\nmails, tasks, drafts, audit log')
box(ax, 0.05, 0.25, 0.40, 0.085, 'Role 2: ActionPlanner\nstate labels + faculty-reply\ndrafts (no send)', bold=True)
box(ax, 0.55, 0.25, 0.40, 0.085, 'Reminder worker\n(24 h / 1 h / overdue,\n15 s tick, once each)')
box(ax, 0.02, 0.09, 0.29, 0.07, 'In-app reminders')
box(ax, 0.355, 0.09, 0.29, 0.07, '.ics calendar export\n(approved only)')
box(ax, 0.69, 0.09, 0.29, 0.07, 'Draft reply\n(copy only)')
arrow(ax, 0.24, 0.905, 0.42, 0.852)
arrow(ax, 0.76, 0.905, 0.58, 0.852)
arrow(ax, 0.5, 0.78, 0.32, 0.717)
arrow(ax, 0.68, 0.78, 0.70, 0.717, dashed=True)
arrow(ax, 0.70, 0.63, 0.32, 0.575, 'rejected if quote\nnot verbatim', lx=-0.24, ly=-0.03)
arrow(ax, 0.25, 0.63, 0.42, 0.577)
arrow(ax, 0.5, 0.50, 0.5, 0.457)
arrow(ax, 0.40, 0.385, 0.25, 0.337)
arrow(ax, 0.60, 0.385, 0.75, 0.337)
arrow(ax, 0.25, 0.25, 0.165, 0.162)
arrow(ax, 0.60, 0.25, 0.50, 0.162)
arrow(ax, 0.75, 0.25, 0.835, 0.162)
ax.plot([0.028,0.028],[0.945,0.125], color='black', lw=0.7, ls=':')
ax.text(0.012, 0.53, 'untrusted', rotation=90, fontsize=6, va='center')
plt.tight_layout(pad=0.15); plt.savefig('paper/fig1_architecture.png', dpi=300); plt.close()

# ---------- Fig 2: lifecycle ----------
fig, ax = plt.subplots(figsize=(3.45, 2.5)); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis('off')
box(ax, 0.03, 0.70, 0.20, 0.16, 'Mail\nimported')
box(ax, 0.31, 0.70, 0.24, 0.16, 'Needs review\n(date + quote shown)')
box(ax, 0.66, 0.70, 0.30, 0.16, 'Approved by user\n(Upcoming)')
box(ax, 0.66, 0.30, 0.30, 0.16, 'Overdue -\nsubmission unverified')
box(ax, 0.31, 0.30, 0.24, 0.16, 'Missing (sample\nClassroom evidence)')
box(ax, 0.03, 0.30, 0.20, 0.16, 'Submitted\n(reported / fixture)')
box(ax, 0.31, 0.02, 0.40, 0.13, 'Revision import -> version +1,\nback to Needs review, old reminders dropped', fs=6.6)
arrow(ax, 0.23, 0.78, 0.31, 0.78, 'extract')
arrow(ax, 0.55, 0.78, 0.66, 0.78, 'approve', lx=0, ly=0.04)
arrow(ax, 0.81, 0.70, 0.81, 0.46, 'clock passes\ndue time', lx=-0.16)
arrow(ax, 0.66, 0.36, 0.55, 0.38, 'synthetic status\nNOT_SUBMITTED', lx=0.03, ly=0.05)
arrow(ax, 0.31, 0.36, 0.23, 0.38, 'TURNED_IN', lx=0, ly=0.04)
arrow(ax, 0.81, 0.30, 0.81, 0.085, 'new mail,\nsame key', lx=-0.16)
arrow(ax, 0.31, 0.085, 0.38, 0.70, dashed=True)
plt.tight_layout(pad=0.15); plt.savefig('paper/fig2_lifecycle.png', dpi=300); plt.close()

# ---------- Fig 3: results ----------
import json
r = json.load(open('/downloads/evalrun/eval_results.json'))
labels = ['Precision', 'Recall', 'F1', 'Decision\nsafety']
app_v = [r['app']['precision']*100, r['app']['recall']*100, r['app']['f1']*100, r['app']['decision_safety']*100]
nb_v  = [r['naive']['precision']*100, r['naive']['recall']*100, r['naive']['f1']*100, r['naive']['decision_safety']*100]
fig, ax = plt.subplots(figsize=(3.45, 2.1))
x = range(len(labels)); w=0.36
b1 = ax.bar([i-w/2 for i in x], nb_v, w, color='0.75', edgecolor='black', lw=0.7, label='Naive first-date baseline')
b2 = ax.bar([i+w/2 for i in x], app_v, w, color='white', edgecolor='black', lw=0.9, hatch='//', label='CampusInbox rules')
for b in list(b1)+list(b2):
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+1.2, f'{b.get_height():.1f}', ha='center', fontsize=6.2)
ax.set_xticks(list(x)); ax.set_xticklabels(labels, fontsize=7)
ax.set_ylabel('%', fontsize=7); ax.set_ylim(0, 118)
ax.legend(fontsize=6.4, frameon=False, loc='lower left')
ax.spines[['top','right']].set_visible(False)
ax.tick_params(labelsize=6.5)
plt.tight_layout(pad=0.15); plt.savefig('paper/fig3_results.png', dpi=300); plt.close()
print("figs done")
