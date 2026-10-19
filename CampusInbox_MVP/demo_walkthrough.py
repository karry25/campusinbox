"""Repeatable HTTP demonstration in a temporary database. Standard library only."""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
from pathlib import Path
from socket import socket

ROOT = Path(__file__).resolve().parent

def main():
    with socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    env = dict(os.environ)
    # This walkthrough is always offline, even if the user's normal server uses a model.
    for key in ('CAMPUS_MODEL_URL', 'CAMPUS_MODEL_KEY', 'CAMPUS_MODEL_NAME'):
        env.pop(key, None)
    with tempfile.TemporaryDirectory() as folder:
        def start():
            proc = subprocess.Popen([sys.executable, str(ROOT/'app.py'), '--port', str(port), '--db', str(Path(folder)/'demo.db')], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(100):
                try:
                    state = json.load(urllib.request.urlopen(base+'/api/state', timeout=1))
                    return proc, state
                except (OSError, ValueError):
                    if proc.poll() is not None:raise RuntimeError('Server stopped before startup.')
                    time.sleep(.1)
            proc.terminate();proc.wait();raise RuntimeError('Server did not start.')
        proc, state = start()
        token = state['token']
        def post(path, data):
            req = urllib.request.Request(base+'/api/'+path, data=json.dumps(data).encode(),headers={'Content-Type':'application/json','X-Campus-Token':token})
            return json.load(urllib.request.urlopen(req,timeout=5))
        def get():return json.load(urllib.request.urlopen(base+'/api/state',timeout=5))
        try:
            post('demo',{})
            assert len(get()['tasks'])==5
            assert get()['reminders']==[]
            print('PASS 1: Five synthetic mails imported. Review gate blocks all reminders.')
            for key in ['agentic-lab','ds-report','ai-presentation']:post('approve',{'id':key})
            assert len(get()['reminders'])==3
            print('PASS 2: Approved deadlines create overdue, 24-hour and 1-hour reminders.')
            post('demo',{});assert len(get()['tasks'])==5;assert len(get()['reminders'])==3
            print('PASS 3: Re-import and refresh create no duplicate tasks or reminders.')
            lab=next(t for t in get()['tasks'] if t['id']=='agentic-lab')
            assert lab['state']=='Overdue - submission unverified'
            post('fixture',{'id':'agentic-lab'})
            assert 'sample Classroom evidence' in next(t for t in get()['tasks'] if t['id']=='agentic-lab')['state']
            print('PASS 4: Email is not missing-submission proof; fixture status is labelled synthetic.')
            post('draft',{'id':'agentic-lab'});post('save-draft',{'id':'agentic-lab','draft':'Reviewed local draft. Not sent.'})
            post('import',json.loads((ROOT/'revision_mail.json').read_text()))
            report=next(t for t in get()['tasks'] if t['id']=='ds-report')
            assert report['review']==1 and report['version']==2
            assert not any(r['task_id']=='ds-report' for r in get()['reminders'])
            print('PASS 5: Revision invalidates approval and removes obsolete reminders.')
            proc.terminate();proc.wait(timeout=10)
            proc,state=start();token=state['token']
            assert next(t for t in state['tasks'] if t['id']=='agentic-lab')['draft']=='Reviewed local draft. Not sent.'
            assert next(t for t in state['tasks'] if t['id']=='ds-report')['version']==2
            print('PASS 6: Draft and revised deadline survive an actual server restart.')
            cal=urllib.request.urlopen(base+'/calendar.ics').read().decode()
            assert cal.count('BEGIN:VEVENT')==2
            print('PASS 7: Calendar export contains only the two still-approved tasks.')
            try:post('send',{'id':'agentic-lab'});raise AssertionError('Send must not exist.')
            except urllib.error.HTTPError as exc:assert exc.code==400
            print('PASS 8: No send endpoint. No real account accessed. Temporary demo data removed on exit.')
        finally:
            proc.terminate();proc.wait(timeout=10)

if __name__=='__main__':main()
