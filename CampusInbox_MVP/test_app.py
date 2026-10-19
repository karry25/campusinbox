"""Offline regression suite; real provider access is not tested."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import app

class CampusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = app.DB
        app.DB = Path(self.tmp.name) / 'test.db'
        app.init_db()
        self.db = app.connect()
        self.mails = json.loads((app.ROOT / 'sample_mails.json').read_text())
    def tearDown(self):
        self.db.close()
        app.DB = self.old
        self.tmp.cleanup()
    def load(self):
        for m in self.mails: app.ingest(self.db, m)
    def approve(self,key):
        return app.action(self.db,'/api/approve',{'id':key})
    def test_explicit_extraction(self):
        e=app.EvidenceExtractor.extract(self.mails[0]); self.assertEqual(e['due_at'],'2026-10-19T20:00:00+05:30'); self.assertIn(e['quote'],self.mails[0]['body'])
    def test_ambiguous_date_held(self):
        self.load(); self.assertRaises(ValueError,self.approve,'ambiguous-review'); self.assertIsNone(app.EvidenceExtractor.extract(self.mails[3])['due_at'])
    def test_review_gate_blocks_reminders(self):
        self.load();app.tick(self.db);self.assertEqual(len(app.snapshot(self.db)['reminders']),0)
    def test_deduplication(self):
        self.load(); self.assertEqual(app.ingest(self.db,self.mails[0]),'duplicate');self.assertEqual(self.db.execute('SELECT count(*) FROM tasks').fetchone()[0],5)
    def test_conflicting_message_id_rejected(self):
        self.load();m=dict(self.mails[0]);m['body']='different';self.assertRaises(ValueError,app.ingest,self.db,m)
    def test_three_reminder_bands_once_each(self):
        self.load();self.approve('ds-report');app.tick(self.db);app.tick(self.db)
        self.assertEqual(len(app.snapshot(self.db)['reminders']),1)
        for clock in ['2026-10-20T17:30:00+05:30','2026-10-20T19:00:00+05:30']:
            app.action(self.db,'/api/clock',{'value':clock});app.tick(self.db);app.tick(self.db)
        self.assertEqual(len(app.snapshot(self.db)['reminders']),3)
    def test_submission_suppresses_reminders(self):
        self.load();self.approve('agentic-lab');app.tick(self.db);app.action(self.db,'/api/status',{'id':'agentic-lab','status':'TURNED_IN'})
        self.assertEqual(app.snapshot(self.db)['reminders'],[])
    def test_email_not_proof_of_missing(self):
        self.load();self.approve('agentic-lab'); t=next(t for t in app.snapshot(self.db)['tasks'] if t['id']=='agentic-lab');self.assertEqual(t['state'],'Overdue - submission unverified')
    def test_fixture_is_labelled_synthetic(self):
        self.load();self.approve('agentic-lab');app.action(self.db,'/api/fixture',{'id':'agentic-lab'});t=next(t for t in app.snapshot(self.db)['tasks'] if t['id']=='agentic-lab');self.assertEqual(t['state'],'Missing (sample Classroom evidence)')
    def test_revision_invalidates_prior_approval(self):
        self.load();self.approve('ds-report');app.tick(self.db)
        rev=json.loads((app.ROOT/'revision_mail.json').read_text())['mails'][0];app.ingest(self.db,rev)
        t=dict(self.db.execute("SELECT * FROM tasks WHERE id='ds-report'").fetchone());self.assertEqual(t['version'],2);self.assertEqual(t['review'],1);self.assertEqual(self.db.execute("SELECT count(*) FROM reminders WHERE task_id='ds-report'").fetchone()[0],0)
    def test_unknown_status_cannot_be_forged(self):
        self.load();self.assertRaises(ValueError,app.action,self.db,'/api/status',{'id':'agentic-lab','status':'NOT_SUBMITTED'})
    def test_draft_persisted_but_never_sent(self):
        self.load();app.action(self.db,'/api/draft',{'id':'agentic-lab'}); t=dict(self.db.execute("SELECT * FROM tasks WHERE id='agentic-lab'").fetchone());self.assertIn('Kareena Jahagirdar',t['draft']); self.assertRaises(ValueError,app.action,self.db,'/api/send',{'id':'agentic-lab'})
    def test_draft_edits_saved(self):
        self.load();app.action(self.db,'/api/save-draft',{'id':'agentic-lab','draft':'My reviewed draft'});self.assertEqual(self.db.execute("SELECT draft FROM tasks WHERE id='agentic-lab'").fetchone()[0],'My reviewed draft')
    def test_calendar_only_approved_utc(self):
        self.load();self.assertNotIn('BEGIN:VEVENT',app.calendar_ics(self.db));self.approve('agentic-lab');cal=app.calendar_ics(self.db);self.assertEqual(cal.count('BEGIN:VEVENT'),1);self.assertIn('DTSTART:20261019T143000Z',cal);self.assertTrue(all(len(l.encode())<=75 for l in cal.split('\r\n')))
    def test_timezone_required(self):
        self.assertRaises(ValueError,app.stamp,'2026-10-20T18:00:00')
    def test_persistence_after_reconnect(self):
        self.load();self.db.commit()
        with app.connect() as other: self.assertEqual(other.execute('SELECT count(*) FROM tasks').fetchone()[0],5)
    def test_mail_instructions_remain_data(self):
        self.load();self.assertEqual(self.db.execute('SELECT count(*) FROM tasks').fetchone()[0],5);self.assertEqual(self.db.execute('SELECT count(*) FROM audit').fetchone()[0],5)
    def test_model_invalid_evidence_rejected(self):
        with patch.dict(os.environ,{'CAMPUS_MODEL_URL':'http://localhost:1234/v1/chat/completions'}),patch.object(app,'model_call',return_value={'due_at':'2026-11-01T00:00:00+05:30','quote':'invented'}):
            self.assertRaises(ValueError,app.EvidenceExtractor.extract,self.mails[0])
    def test_model_mock_valid_evidence(self):
        due='2026-10-19T20:00:00+05:30'
        with patch.dict(os.environ,{'CAMPUS_MODEL_URL':'http://localhost:1234/v1/chat/completions'}),patch.object(app,'model_call',return_value={'due_at':due,'quote':'Due: '+due}):
            self.assertEqual(app.EvidenceExtractor.extract(self.mails[0])['engine'],'model proposal')
    def test_model_mock_abstains_on_ambiguity(self):
        with patch.dict(os.environ,{'CAMPUS_MODEL_URL':'http://localhost:1234/v1/chat/completions'}),patch.object(app,'model_call',return_value={'due_at':None,'quote':''}):
            self.assertIsNone(app.EvidenceExtractor.extract(self.mails[3])['due_at'])
    def test_batch_rollback(self):
        with self.assertRaises(ValueError):
            with app.connect() as db:app.action(db,'/api/import',{'mails':[self.mails[0],{'id':'bad'}]})
        self.assertEqual(self.db.execute('SELECT count(*) FROM mails').fetchone()[0],0)
    def test_eml_import(self):
        path=Path(self.tmp.name)/'sample.eml';path.write_text('Subject: Demo\nMessage-ID: <test-local>\nContent-Type: text/plain; charset=utf-8\n\nCourse: AI\nTask: Demo\nDue: 2026-10-20T12:00:00+05:30\n')
        self.assertEqual(app.ingest(self.db,app.read_eml(path)),'created')
    def test_invalid_mail_shape(self):
        self.assertRaises(ValueError,app.ingest,self.db,42)

if __name__=='__main__':unittest.main(verbosity=2)
