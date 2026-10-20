'use strict';
let state = null, view = null, busy = false;
const $ = id => document.getElementById(id);
const el = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
const format = v => v ? new Date(v).toLocaleString('en-IN', {timeZone: 'Asia/Kolkata', dateStyle: 'medium', timeStyle: 'short'}) + ' IST' : 'No verified date';
const feedback = t => { $('feedback').textContent = t; };
async function refresh() {
  const r = await fetch('/api/state'); if (!r.ok) throw Error('Could not read local state'); state = await r.json();
  const a = await fetch('/api/assistant'); view = a.ok ? await a.json() : null; render();
}
async function post(path, data = {}) {
  const r = await fetch('/api/' + path, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Campus-Token': state.token}, body: JSON.stringify(data)});
  const out = await r.json(); if (!r.ok) throw Error(out.error); return out;
}
async function act(path, data = {}) {
  if (busy) return; busy = true;
  try { const out = await post(path, data); feedback(out.message); await refresh(); } catch (e) { feedback(e.message); } finally { busy = false; }
}
function button(text, fn, cls) { const b = el('button', text); if (cls) b.className = cls; b.addEventListener('click', fn); return b; }
function stat(name, n) { const b = el('div', undefined, 'stat'); b.append(el('strong', String(n)), el('span', name)); return b; }
function evidence(t) { const d = el('details'); d.append(el('summary', 'Source mail and evidence'), el('p', t.mail.subject), el('div', t.mail.body, 'source')); if (t.quote) d.append(el('p', 'Evidence quote (checked against the mail text):', 'meta'), el('div', t.quote, 'quote')); return d; }
function card(t) {
  const c = el('article', undefined, 'task'); c.dataset.task = t.id;
  const tag = el('span', t.state, 'tag' + (t.review ? ' rev' : ''));
  c.append(el('div', t.course, 'course'), el('h3', t.title), tag, el('p', format(t.due_at), 'due'), el('p', `Version ${t.version} · ${t.engine} · status: ${t.status_source}`, 'meta'));
  if (t.review) {
    c.append(el('p', t.reason, 'meta'));
    const label = el('label', 'Verify the deadline against the source (ISO + timezone)'); const input = el('input'); input.value = t.due_at || ''; input.placeholder = '2026-10-23T17:00:00+05:30'; label.append(input);
    c.append(label, button('Approve deadline', () => act('approve', {id: t.id, due_at: input.value}), 'primary'));
  }
  c.append(evidence(t));
  const ctl = el('div', undefined, 'controls');
  ctl.append(button('Mark submitted', () => act('status', {id: t.id, status: 'TURNED_IN'})), button('Reset status', () => act('status', {id: t.id, status: 'UNKNOWN'})), button('Draft faculty reply', () => act('draft', {id: t.id})));
  if (t.id === 'agentic-lab') ctl.append(button('Load sample Classroom status', () => act('fixture', {id: t.id})));
  c.append(ctl);
  if (t.draft) {
    const label = el('label', 'Editable draft. Never sent by this app.'); const ta = el('textarea'); ta.rows = 8; ta.value = t.draft; label.append(ta);
    c.append(label, button('Save draft edits', () => act('save-draft', {id: t.id, draft: ta.value})), button('Copy edited draft', async () => { try { await navigator.clipboard.writeText(ta.value); feedback('Copied. Review the recipient and words yourself before sending.'); } catch (e) { feedback('Clipboard unavailable. Select and copy manually.'); } }));
  }
  return c;
}
function traceBlock(t) {
  const c = el('article', undefined, 'task'); c.append(el('div', t.course, 'course'), el('h3', t.title), el('p', t.reason, 'meta'));
  c.append(el('h4', 'Tool loop'));
  (t.trace || []).forEach(s => { const r = el('div', undefined, 'step'); r.append(el('b', 'step ' + (s.step ?? '')), el('span', (s.action || '?') + ' ' + JSON.stringify(s.args || s.result || s.gate || '').slice(0, 220))); c.append(r); });
  if (!(t.trace || []).length) c.append(el('p', 'No trace recorded.', 'meta'));
  c.append(el('h4', 'Messages between roles'));
  (t.messages || []).forEach(m => { const r = el('div', undefined, 'step'); r.append(el('b', m.sender + ' → ' + m.receiver), el('span', m.kind + ': ' + String(m.content).slice(0, 260))); c.append(r); });
  return c;
}
function render() {
  $('engine').textContent = state.engine + '.'; $('clock').textContent = (state.mode === 'demo' ? 'Demo time: ' : 'Device time: ') + format(state.clock);
  const T = state.tasks;
  const home = $('home'); home.replaceChildren();
  const stats = el('div', undefined, 'stats'); stats.append(stat('Mails / tasks', T.length), stat('Need review', T.filter(t => t.review).length), stat('Active reminders', state.reminders.length), stat('Conflicts', view ? view.conflicts.length : 0)); home.append(stats);
  home.append(el('h2', 'Priority'));
  if (view && view.priority.length) view.priority.forEach(p => { const b = el('div', undefined, 'bar'); const d = el('div'); d.append(el('strong', p.title), el('div', p.course + ' · ' + format(p.due_at), 'meta')); b.append(el('span', '#' + p.rank, 'rank'), d, el('span', p.label, 'tag')); home.append(b); });
  else home.append(el('p', 'Approve a deadline to see it ranked here. Only approved, not-submitted tasks are ranked.', 'empty'));
  home.append(el('h2', 'Weekly digest'), el('pre', view ? view.digest : ''));
  if (view && view.conflicts.length) { home.append(el('h2', 'Conflicts')); view.conflicts.forEach(c => home.append(el('p', `'${c[0]}' and '${c[1]}' are ${Number(c[2]).toFixed(1)} h apart.`))); }
  const tasks = $('tasks'); tasks.replaceChildren(); const cards = el('div', undefined, 'cards'); T.forEach(t => cards.append(card(t)));
  tasks.append(T.length ? cards : el('p', 'Load the sample mails to begin. Every extracted deadline starts in review.', 'empty'));
  const tr = $('trace'); tr.replaceChildren(el('h2', 'Agent trace'), el('p', 'For each mail: the tool calls the Extractor made, then the Verifier\'s decision. Offline, the trace comes from a scripted run of the same tools with no model.', 'meta'));
  const tc = el('div', undefined, 'cards'); T.forEach(t => tc.append(traceBlock(t))); tr.append(T.length ? tc : el('p', 'No tasks yet.', 'empty'));
  const rm = $('reminders'); rm.replaceChildren(el('h2', 'In-app reminders'), el('p', 'Stored once per task version and time band. Reminders go to the owner only; submitted tasks are suppressed.', 'meta'));
  if (!state.reminders.length) rm.append(el('p', 'No active reminders. Approve a deadline and move the demo clock into its reminder window.', 'empty'));
  state.reminders.forEach(r => { const n = el('div', undefined, 'event'); n.append(el('strong', r.title + ' - ' + r.label), el('div', format(r.fired_at) + ' · version ' + r.version, 'meta')); rm.append(n); });
  const au = $('audit'); au.replaceChildren(el('h2', 'Activity log')); state.audit.forEach(a => { const n = el('div', undefined, 'event'); n.append(el('strong', a.event), el('div', a.detail), el('small', format(a.at))); au.append(n); });
  renderAbout();
}
function table(head, rows) { const t = el('table'); const h = el('tr'); head.forEach(x => h.append(el('th', x))); t.append(h); rows.forEach(r => { const tr = el('tr'); r.forEach(x => tr.append(el('td', x))); t.append(tr); }); return t; }
function renderAbout() {
  const a = $('about'); if (a.dataset.done) return; a.dataset.done = '1';
  a.append(el('h2', 'What it is'), el('p', 'CampusInbox reads college mails, proposes deadlines with a quoted source line, and asks the student to approve each date before any reminder is scheduled. It is a student project prototype, not a released product.'));
  a.append(el('h2', 'Who it is for (analysis, not measured)'), table(['User', 'Problem', 'How it helps'], [['Student', 'Deadlines hidden in long mails', 'Evidence-backed list, reminders, digest'], ['Class representative', 'Relays notices to many students', 'Planned: shared review queue'], ['Faculty', 'Repeated "when is it due?" questions', 'Fewer ambiguous notices; planned: none, the app does not message faculty']]));
  a.append(el('h2', 'Cost and privacy (analysis)'), el('p', 'Runs locally with no model and no network by default. Model mode is opt-in and sends mail text to the model endpoint the user configures, so it needs the user\'s own consent per mailbox. Gmail import is read-only and runs on the user\'s machine. No usage, market or revenue numbers are claimed.'));
  a.append(el('h2', 'Roadmap'), table(['Item', 'Status'], [['Mail import, extraction, verifier, approval, reminders, digest, chat', 'Built and unit-tested'], ['Gmail read-only OAuth', 'Implemented, not live-tested'], ['WhatsApp Cloud and email reminder adapters', 'Stub, off by default, not live-tested'], ['Classroom and Calendar sync', 'Planned'], ['Embedding retrieval, multi-agent planner, user study', 'Planned']]));
}
function addMsg(text, who, src) { const m = el('div', text, 'msg ' + who); if (src) m.append(el('span', src, 'src')); $('chatlog').append(m); $('chatlog').scrollTop = 1e6; }
async function ask(q) {
  if (!q.trim() || !state) return; addMsg(q, 'u');
  try { const out = await post('ask', {text: q}); addMsg(out.reply, 'a', out.evidence + (out.mode ? ' · ' + out.mode : '')); } catch (e) { addMsg(e.message, 'a'); }
}
document.querySelectorAll('[data-tab]').forEach(b => b.addEventListener('click', () => { document.querySelectorAll('.view').forEach(v => v.hidden = v.id !== b.dataset.tab); document.querySelectorAll('[data-tab]').forEach(x => x.classList.toggle('selected', x === b)); }));
document.querySelectorAll('[data-q]').forEach(b => b.addEventListener('click', () => ask(b.dataset.q)));
$('askform').addEventListener('submit', e => { e.preventDefault(); const q = $('askbox').value; $('askbox').value = ''; ask(q); });
$('load').onclick = () => act('demo'); $('refresh').onclick = () => refresh().catch(e => feedback(e.message)); $('setclock').onclick = () => act('clock', {value: $('clock-input').value}); $('liveclock').onclick = () => act('liveclock');
$('import').onclick = () => { try { act('import', JSON.parse($('import-text').value)); } catch (e) { feedback('Invalid JSON: ' + e.message); } };
refresh().catch(e => feedback(e.message));
setInterval(() => { if (!busy && !document.querySelector('textarea:focus,input:focus')) refresh().catch(() => {}); }, 60000);
