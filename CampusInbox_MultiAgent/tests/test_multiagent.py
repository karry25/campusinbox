import sys, pathlib, unittest
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from campusinbox_ma.tools.core import (Mail, parse_date, find_deadline_sentences,
                                       verify_quote, detect_injection, tag_course)
from campusinbox_ma.agents.base import State
from campusinbox_ma.coordinator import Coordinator
from campusinbox_ma.chatbot import ChatbotAgent
from campusinbox_ma.demo import load_demo_mails


class TestTools(unittest.TestCase):
    def test_parse_numeric_date(self):
        self.assertEqual(parse_date("deadline is 26/10/2026", date(2026, 10, 20)), date(2026, 10, 26))

    def test_parse_named_date(self):
        self.assertEqual(parse_date("viva on 28 October 2026", date(2026, 10, 20)), date(2026, 10, 28))
        self.assertEqual(parse_date("test is on 2 Nov 2026", date(2026, 10, 20)), date(2026, 11, 2))

    def test_parse_relative(self):
        self.assertEqual(parse_date("closes tomorrow", date(2026, 10, 21)), date(2026, 10, 22))
        self.assertEqual(parse_date("submit by Friday", date(2026, 10, 20)), date(2026, 10, 23))

    def test_candidate_sentences(self):
        mail = load_demo_mails()[0]
        hits = find_deadline_sentences(mail)
        self.assertTrue(any("26/10/2026" in h for h in hits))

    def test_verify_quote(self):
        mail = load_demo_mails()[0]
        self.assertTrue(verify_quote(mail, "the revised report submission deadline is 26/10/2026."))
        self.assertFalse(verify_quote(mail, "deadline is 1 January 2027"))

    def test_injection_detected(self):
        mail = [m for m in load_demo_mails() if "unknown" in m.sender][0]
        self.assertTrue(detect_injection(mail))

    def test_course_tags(self):
        self.assertEqual(tag_course("Agentic AI mini project viva"), "Agentic AI")
        self.assertEqual(tag_course("Submit the MapReduce assignment"), "DS")
        self.assertEqual(tag_course("campus drive registration"), "Placement")


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.state = Coordinator().run(State(mails=load_demo_mails()))

    def test_deadlines_extracted(self):
        dues = {dl.due for dl in self.state.verified}
        self.assertIn(date(2026, 10, 26), dues)
        self.assertIn(date(2026, 10, 28), dues)
        self.assertIn(date(2026, 10, 22), dues)  # 'tomorrow' vs mail date

    def test_course_tagging_and_grouping(self):
        courses = {dl.course for dl in self.state.verified}
        self.assertIn("Agentic AI", courses)
        self.assertIn("Placement", courses)

    def test_injection_mail_blocked(self):
        self.assertTrue(any("injection" in r["reason"] for r in self.state.rejected))
        self.assertFalse(any("unknown" in dl.mail_subject or "quiz" in dl.what.lower()
                             and "27 October" in dl.quote for dl in self.state.verified))

    def test_reminders_are_preview_only(self):
        for item in self.state.planned:
            self.assertIn("preview only", item["reminder"]["status"])


class TestChatbot(unittest.TestCase):
    def setUp(self):
        state = Coordinator().run(State(mails=load_demo_mails()))
        self.bot = ChatbotAgent(state, live_web=False)

    def test_tool_selection_web(self):
        calls = self.bot.pick_tools("search the web for LangGraph")
        self.assertEqual(calls[0][0], "web_search")

    def test_web_fallback_labelled(self):
        out = self.bot.ask("search the web for LangGraph")
        self.assertIn("demo-fallback", out)

    def test_course_query(self):
        out = self.bot.ask("show placement deadlines")
        self.assertIn("campus drive", out.lower())

    def test_lists_deadlines(self):
        out = self.bot.ask("what is due?")
        self.assertIn("deadlines", out.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestNoterAgent(unittest.TestCase):
    def setUp(self):
        self.state = Coordinator().run(State(mails=load_demo_mails()))

    def test_noter_runs_after_planner(self):
        self.assertTrue(self.state.planned)
        for item in self.state.planned:
            self.assertIn("note", item)

    def test_notes_have_priority_and_step(self):
        for item in self.state.planned:
            note = item["note"]
            self.assertIn(note["priority"], ("high", "medium", "low", "OVERDUE"))
            self.assertTrue(note["first_step"])
            self.assertEqual(note["status"], "note only - nothing sent")

    def test_notes_stored_on_deadline(self):
        for item in self.state.planned:
            self.assertTrue(item["deadline"].notes)


class TestVectorStore(unittest.TestCase):
    def setUp(self):
        from campusinbox_ma.tools.vectorstore import VectorStore
        self.store = VectorStore()
        for m in load_demo_mails():
            self.store.add_mail(m.subject, m.body)

    def test_indexes_sentences(self):
        self.assertGreater(len(self.store), 5)

    def test_retrieves_relevant_sentence(self):
        hits = self.store.search("MapReduce assignment")
        self.assertTrue(hits)
        self.assertIn("MapReduce", hits[0]["text"])
        self.assertEqual(hits[0]["source"], "Distributed Systems lab assignment 4")

    def test_scores_are_sorted_and_cited(self):
        hits = self.store.search("viva")
        scores = [h["score"] for h in hits]
        self.assertEqual(scores, sorted(scores, reverse=True))
        for h in hits:
            self.assertTrue(h["source"])

    def test_no_match_returns_empty(self):
        self.assertEqual(self.store.search("xylophone zzz qqq"), [])


class TestReactLoop(unittest.TestCase):
    def setUp(self):
        state = Coordinator().run(State(mails=load_demo_mails()))
        self.bot = ChatbotAgent(state, live_web=False)

    def test_trace_has_thought_action_observation(self):
        out = self.bot.ask("show placement deadlines")
        self.assertIn("Thought:", out)
        self.assertIn("Action: deadlines_for_course", out)
        self.assertIn("Observation:", out)
        self.assertIn("Final answer:", out)

    def test_open_question_uses_vector_search(self):
        result = self.bot.react("when is the MapReduce assignment due?")
        self.assertIn("search_mails", result["trace"])
        self.assertIn("MapReduce", result["answer"])

    def test_step_cap(self):
        result = self.bot.react("search the web for LangGraph and what is next and list all deadlines")
        self.assertLessEqual(result["steps"], 4)

    def test_multistep_trace(self):
        out = self.bot.ask("what is next and search the web for prompt injection")
        self.assertGreaterEqual(out.count("Thought:"), 3)  # 2 steps + final thought
        self.assertIn("demo-fallback", out)
