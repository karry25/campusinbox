import json
P = {
1:("N","Only says a final estimate is expected \"by Friday\"; sender's own timing, reader is not asked to do something by then."),
2:("D 2001-11-07","\"hoping to get this approved by Wednesday Tokyo time\" (mail is Mon 5 Nov 2001); weak, it is a target."),
3:("N","Internal discussion of water sampling, no date."),
4:("N","Birthday thanks."),
5:("N","Quotes a contract clause (payment due on the 25th); a recurring term, not a deadline for this mail."),
6:("X","Mail is cut off in the sheet; says tags must be in \"no later than an hour before schedule flows\" for 07/01 and 07/02, several relative times."),
7:("N","Personal note, no deadline."),
8:("X","Funds expected \"either Jan 12 or 15\" and wire \"before 2:00\"; two possible dates, nobody is asked to act by one."),
9:("D 2000-03-21","\"I have established Tuesday, March 21st as the deadline for responding.\""),
10:("D 2001-05-25","\"completed by Friday, May 25, 2001.\""),
11:("D 2001-10-26","\"all trades ... must be completed by 3:00 PM CST Friday, October 26.\""),
12:("N","Asks \"Do you want to bid anyway? Let me know.\" No date."),
13:("N","Seminar on Nov 1 with \"Please RSVP\" but no RSVP date. Event date only."),
14:("N","News article; no one is asked to do anything."),
15:("N","\"call me ... next week, starting Thu\"; an invitation, not a deadline."),
16:("N","\"I can FEDEX the tickets to you by Friday\"; the sender's own offer."),
17:("D 2001-05-25","\"completed by Friday, May 25, 2001.\""),
18:("X","\"we need to reply by mid next week\" (mail Fri 2 Nov 2001): vague, roughly 7 Nov."),
19:("N","Orientation on Feb 7 is an event; \"PLEASE RSVP\" has no date."),
20:("D 2000-04-03","\"we need to pay by monday\" (mail Thu 30 Mar 2000, so Mon 3 Apr)."),
21:("N","Only relative periods (\"30 days prior\", \"15 days\"), no calendar date."),
22:("D 2001-10-19","\"advise the Secretary ... by no later than October 19, 2001.\""),
23:("N","Asks whether a deadline was set; answer is \"last class + a few days\", no date."),
24:("N","Interview scheduled Monday Sept 18 is an event; no reply deadline."),
25:("D 2002-02-05","\"send an e-mail to Amy Fitzpatrick by noon on Tuesday\" (mail Mon 4 Feb 2002)."),
26:("N","Procedure changes on Oct 26; informational."),
27:("N","No deadline; valuation discussion."),
28:("D 2002-01-23","\"extended the registration deadline until this Wednesday, January 23rd, 2002.\""),
29:("N","Chat; \"by Thursday\" is about losing weight."),
30:("D 2001-03-21","\"Please respond by 10 a.m. on Wednesday, March 21.\""),
31:("N","Workshop on Sept 12 is an event; RSVP has no date."),
32:("X","Several: certification \"no later than February 11, 2002\" and \"48 hours\" / Thursday night for drive copying."),
33:("N","Empty body, only a subject line."),
34:("N","Lunch chat."),
35:("D 2001-02-02","\"Please return your comments to me by Friday, Feb. 2.\""),
36:("N","Status update; \"model by EOD tomorrow\" is the sender's own promise."),
37:("N","\"timesheet due date is quickly approaching\" but no date given."),
38:("N","Draft sent; no deadline."),
39:("X","Several: plans \"due on Jan 7\", budget \"due Jan 3, 2002\"."),
40:("N","Cards will be available \"by tomorrow morning\"; not something the reader must do."),
41:("X","Five case due dates (11/6, 11/13, 11/20, 11/27, 12/4)."),
42:("N","Personal schedule reminder."),
43:("N","FYI news item; the Governor decides \"no later than the end of September\", not the reader."),
44:("N","RSVP request, no date."),
45:("D 2001-05-25","\"completed by Friday, May 25, 2001.\""),
46:("X","Two deadlines: drops Sept 15, enrollments Sept 20, 2001."),
47:("D 2001-11-13","\"hearing back from you by Tuesday morning (Nov. 13).\""),
48:("D 2001-05-02","\"Please respond by 10:00 a.m. on Wednesday, May 2.\""),
49:("D 2001-05-14","\"get your entry form ... to me before Monday, May 14.\""),
50:("N","Meeting is May 18 (event); \"RSVP as soon as possible\" has no date."),
}
K = {k['n']: k for k in json.load(open('adjudication_key.json'))}
json.dump({n: {'answer': a, 'reason': r} for n, (a, r) in P.items()}, open('ai_proposals.json', 'w'), indent=1)
# agreement with the stored AI labels (computed AFTER the proposals were written)
def lab(d, amb): return 'X' if amb else ('N' if d is None else 'D ' + d)
for who in ('A', 'B'):
    ok = sum(lab(K[n][who], K[n][who+'_amb']) == a for n, (a, _) in P.items()); print(who, ok, '/ 50')
ag = [n for n in P if K[n]['kind']=='check']; print('agreed-subset: mine==silver', sum(lab(K[n]['A'],K[n]['A_amb'])==P[n][0] for n in ag), '/', len(ag))
from reportlab.lib.pagesizes import A5
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from xml.sax.saxutils import escape
st = getSampleStyleSheet(); body = ParagraphStyle('b', parent=st['BodyText'], fontSize=11, leading=14)
doc = SimpleDocTemplate('prefilled_sheet.pdf', pagesize=A5, leftMargin=24, rightMargin=24, topMargin=26, bottomMargin=26)
fl = [Paragraph('CampusInbox label check - pre-filled by the assistant', st['Title']),
 Paragraph('These are the assistant\'s PROPOSED answers for the 50 mails on the earlier sheet (item numbers are the same). Please check them against the mails on that sheet. <b>Reply with just the item numbers you disagree with</b>, and if you want, your answer for them (e.g. "7 D 2001-05-09, 12 N"). Say "all fine" if you agree with everything. <b>D date</b> = the date by which someone must do something. <b>N</b> = no deadline. <b>X</b> = several or unclear dates. Event dates are not deadlines. Relative days count from the mail date. Note: a pre-filled sheet can nudge you toward my answers, so please read the mail first; the paper will say that these labels are AI-proposed and human-reviewed.', body), Spacer(1, 8)]
groups = [('A. Proposed DEADLINE (D)', lambda a: a.startswith('D')), ('B. Proposed NO deadline (N)', lambda a: a == 'N'), ('C. Proposed UNCLEAR / several dates (X)', lambda a: a == 'X')]
for title, f in groups:
    fl.append(Paragraph(title, st['Heading2']))
    for n in sorted(P):
        a, r = P[n]
        if f(a): fl += [Paragraph(f'<b>{n}. {escape(a)}</b> - {escape(r)}', body), Spacer(1, 5)]
doc.build(fl)
