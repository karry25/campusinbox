'use strict';
let state = null;
let busy = false;
const $ = id => document.getElementById(id);
const el = (tag, text, cls) => { const n = document.createElement(tag); if(text !== undefined)n.textContent=text; if(cls)n.className=cls; return n; };
const format = value => value ? new Date(value).toLocaleString('en-IN',{timeZone:'Asia/Kolkata',dateStyle:'medium',timeStyle:'short'})+' IST' : 'No verified date';
function feedback(text){ $('feedback').textContent=text; }
async function refresh(){ const r=await fetch('/api/state'); if(!r.ok)throw Error('Could not read local state'); state=await r.json(); render(); }
async function act(path, data={}){ if(busy)return; busy=true; try{const r=await fetch('/api/'+path,{method:'POST',headers:{'Content-Type':'application/json','X-Campus-Token':state.token},body:JSON.stringify(data)});const out=await r.json();if(!r.ok)throw Error(out.error);feedback(out.message);await refresh();}catch(e){feedback(e.message);}finally{busy=false;} }
function button(text, fn){ const b=el('button',text); b.addEventListener('click',fn); return b; }
function render(){
 $('engine').textContent=state.engine; $('clock').textContent=(state.mode==='demo'?'Demo time: ':'Device time: ')+format(state.clock);
 $('stats').replaceChildren();
 const counters=[['Mails / tasks',state.tasks.length],['Need review',state.tasks.filter(t=>t.review).length],['Active reminders',state.reminders.length],['Drafts (not sent)',state.tasks.filter(t=>t.draft).length]];
 counters.forEach(([name,count])=>{const box=el('div',undefined,'stat');box.append(el('strong',String(count)),el('span',name));$('stats').append(box);});
 $('tasks').replaceChildren();const cards=el('div',undefined,'cards');
 state.tasks.forEach(t=>{
   const c=el('article',undefined,'task');c.dataset.task=t.id;
   c.append(el('div',t.course,'course'),el('h3',t.title),el('span',t.state,'tag'),el('p',format(t.due_at),'due'),el('p',`Version ${t.version} · ${t.engine} · status: ${t.status_source}`,'meta'));
   if(t.review){ c.append(el('p',t.reason,'meta'));const label=el('label','Verify deadline against source (ISO + timezone)');const input=el('input');input.value=t.due_at||'';input.placeholder='2026-10-23T17:00:00+05:30';label.append(input);c.append(label,button('Approve deadline',()=>act('approve',{id:t.id,due_at:input.value}))); }
   const source=el('details');source.append(el('summary','Read source mail / evidence'),el('p',t.mail.subject),el('div',t.mail.body,'source'));if(t.quote)source.append(el('p','Extracted evidence: '+t.quote,'meta'));c.append(source);
   const controls=el('div',undefined,'controls');controls.append(button('Mark submitted',()=>act('status',{id:t.id,status:'TURNED_IN'})),button('Reset status',()=>act('status',{id:t.id,status:'UNKNOWN'})),button('Draft faculty reply',()=>act('draft',{id:t.id})));
   if(t.id==='agentic-lab')controls.append(button('Load sample Classroom status',()=>act('fixture',{id:t.id})));
   c.append(controls);
   if(t.draft){const label=el('label','Editable draft. Save changes locally before leaving this view. Never sent.');const text=el('textarea');text.rows=8;text.value=t.draft;label.append(text);c.append(label,button('Save draft edits',()=>act('save-draft',{id:t.id,draft:text.value})),button('Copy edited draft',async()=>{try{await navigator.clipboard.writeText(text.value);feedback('Copied. Review the recipient and words yourself before sending.');}catch(e){feedback('Clipboard unavailable. Select and copy the draft text manually.');}}));}
   cards.append(c);
 });
 $('tasks').append(state.tasks.length?cards:el('p','Load the sample mails to begin. Every extracted deadline starts in review.','empty'));
 $('reminders').replaceChildren(el('h2','In-app reminders'));
 $('reminders').append(el('p','Stored once per task version and time band. No WhatsApp messages are sent. Submitted tasks are suppressed.'));
 if(!state.reminders.length)$('reminders').append(el('p','No active reminders. Approve a deadline and move the demo clock into its reminder window.','empty'));
 state.reminders.forEach(r=>{const n=el('div',undefined,'event');n.append(el('strong',r.title+' - '+r.label),el('small',format(r.fired_at)+' · version '+r.version));$('reminders').append(n);});
 $('audit').replaceChildren(el('h2','Activity log'));
 state.audit.forEach(a=>{const n=el('div',undefined,'event');n.append(el('strong',a.event),el('div',a.detail),el('small',format(a.at)));$('audit').append(n);});
}
document.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('.view').forEach(v=>v.hidden=v.id!==b.dataset.tab);document.querySelectorAll('[data-tab]').forEach(x=>x.classList.toggle('selected',x===b));}));
$('load').onclick=()=>act('demo');$('refresh').onclick=()=>refresh().catch(e=>feedback(e.message));$('setclock').onclick=()=>act('clock',{value:$('clock-input').value});$('liveclock').onclick=()=>act('liveclock');$('import').onclick=()=>{try{act('import',JSON.parse($('import-text').value));}catch(e){feedback('Invalid JSON: '+e.message);}};
refresh().catch(e=>feedback(e.message));
// Refresh state only, preserving in-progress edits in the task view. Worker scheduling is server-side.
setInterval(()=>{if(!busy && !document.querySelector('textarea:focus,input:focus')) refresh().catch(()=>{});},60000);
