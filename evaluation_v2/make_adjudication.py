"""Build the human adjudication sheet: all A/B disputes + a seeded random sample of agreed mails (answers hidden)."""
import json, random
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from xml.sax.saxutils import escape
S = json.load(open("enron_sample_labelled.json"))
both = [m for m in S if m["labels"]["A"] and m["labels"]["B"]]
def agree(m):
    a, b = m["labels"]["A"], m["labels"]["B"]; return a["due"] == b["due"] and a["ambiguous"] == b["ambiguous"]
dis = [m for m in both if not agree(m)]; ag = [m for m in both if agree(m) and len(m["body"]) < 1800]; rnd = random.Random(99); rnd.shuffle(ag)
items = [(m, "dispute") for m in dis] + [(m, "check") for m in ag[:26]]; rnd.shuffle(items); key = []
st = getSampleStyleSheet(); doc = SimpleDocTemplate("adjudication_sheet.pdf", pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
fl = [Paragraph("CampusInbox - label check sheet (Kareena)", st["Title"]),
      Paragraph("Each item is a real, public Enron email (2000-2002). For each, say which calendar date is the DEADLINE: a date by which someone must DO something (reply, submit, send, pay). Relative dates ('Friday') are counted from the mail's date shown. A plain event or meeting date is NOT a deadline unless something must be done by it. Answer with the item number and one of: <b>D yyyy-mm-dd</b> (the deadline date), <b>N</b> (no deadline), <b>X</b> (several/unclear dates). Example: <i>1 D 2001-05-09, 2 N, 3 X</i>. If an item is too long to judge, answer ? and skip it. About 50 items; there are no trick items. You do not see what the AI labellers said.", st["BodyText"]), Spacer(1, 8)]
for i, (m, kind) in enumerate(items, 1):
    d = date.fromisoformat(m["date"][:10]); body = m["body"][:1800] + (" ..." if len(m["body"]) > 1800 else "")
    fl += [Paragraph(f"<b>{i}.</b> Mail date: <b>{d.isoformat()} ({d.strftime('%A')})</b> &nbsp; Subject: {escape(m['subject'])[:120]}", st["Heading4"]), Paragraph(escape(body).replace("\n", "<br/>"), st["BodyText"]), Spacer(1, 12)]
    key.append(dict(n=i, id=m["id"], kind=kind, A=m["labels"]["A"]["due"], A_amb=m["labels"]["A"]["ambiguous"], B=m["labels"]["B"]["due"], B_amb=m["labels"]["B"]["ambiguous"]))
doc.build(fl); json.dump(key, open("adjudication_key.json", "w"), indent=1); print(len(items), "items;", len(dis), "disputes")
