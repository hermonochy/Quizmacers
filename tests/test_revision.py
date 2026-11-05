import random
import sqlite3
import tempfile
import unittest
from pathlib import Path

from quizmancers.combat import Duel
from quizmancers.question_database import DatabaseBank, QuestionDatabase
from quizmancers.questions import MultiplicationBank, Question
from quizmancers.revision import RevisionRecord


class RevisionTrackingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database = QuestionDatabase(Path(self.directory.name) / "questions.db")
        self.database.initialise()

    def tearDown(self):
        self.directory.cleanup()

    def test_schema_is_created_in_existing_questions_database(self):
        with sqlite3.connect(self.database.path) as connection:
            names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertIn("questions", names)
        self.assertIn("revision_progress", names)

    def test_incorrect_answer_persists_between_sessions(self):
        question = self.database.questions("Biology")[0]
        revision = self.database.revision("Biology")
        revision.record(question, False)
        reopened = self.database.revision("Biology")
        self.assertEqual(reopened.get(question.key).attempts, 1)
        self.assertEqual(reopened.get(question.key).incorrect, 1)
        self.assertTrue(reopened.get(question.key).needs_review)
        self.assertEqual(reopened.summary.to_review, 1)

    def test_repeated_success_reduces_review_priority_until_mastered(self):
        question = self.database.questions("History")[0]
        revision = self.database.revision("History")
        revision.record(question, False)
        weights = [revision.priority(question.key)]
        for _ in range(3):
            revision.record(question, True)
            weights.append(revision.priority(question.key))
        self.assertEqual(sorted(weights, reverse=True), weights)
        self.assertLess(weights[-1], 1)
        self.assertFalse(revision.get(question.key).needs_review)
        self.assertTrue(revision.get(question.key).mastered)
        self.assertEqual(revision.summary.mastered, 1)
        self.assertEqual(revision.summary.accuracy, 75)

    def test_missed_answer_after_mastery_needs_review_again(self):
        question = self.database.questions("English")[0]
        revision = self.database.revision("English")
        for _ in range(3):
            revision.record(question, True)
        self.assertTrue(revision.get(question.key).mastered)
        revision.record(question, False)
        self.assertFalse(revision.get(question.key).mastered)
        self.assertTrue(revision.get(question.key).needs_review)

    def test_timeout_counts_once_and_is_saved(self):
        duel = Duel(seed=13, topic="Physics", database=self.database)
        question = duel.player_question
        duel.ai_answer_at = 1000
        duel.update(0.1)
        duel.player_question_elapsed = duel.question_duration - 0.02
        duel.update(0.1)
        self.assertTrue(duel.player_waiting)
        for _ in range(5):
            duel.update(0.1)
        record = self.database.revision("Physics").get(question.key)
        self.assertEqual(record.attempts, 1)
        self.assertEqual(record.incorrect, 1)
        self.assertEqual(record.timeouts, 1)

    def test_invalid_answer_is_not_logged(self):
        duel = Duel(seed=25, topic="Geography", database=self.database)
        self.assertIsNone(duel.submit_answer("wrong"))
        self.assertIsNone(duel.submit_answer("9"))
        self.assertEqual(self.database.revision("Geography").summary.attempts, 0)

    def test_ai_answers_do_not_change_human_revision_stats(self):
        duel = Duel(seed=3, topic="Computing", database=self.database)
        duel.ai_answer_at = 0.01
        duel.update(0.1)
        self.assertEqual(self.database.revision("Computing").summary.attempts, 0)

    def test_topic_progress_does_not_bleed_into_other_subjects(self):
        question = self.database.questions("Chemistry")[0]
        self.database.revision("Chemistry").record(question, False)
        self.assertEqual(self.database.revision("Biology").summary.to_review, 0)

    def test_times_table_reversed_facts_share_one_review_record(self):
        self.assertEqual(Question(7, 8).key, Question(8, 7).key)
        revision = self.database.revision("Times Tables")
        revision.record(Question(7, 8), False)
        self.assertTrue(self.database.revision("Times Tables").get(Question(8, 7).key).needs_review)
        revision.record(Question(8, 7), True)
        self.assertEqual(revision.summary.practised, 1)
        self.assertEqual(revision.summary.attempts, 2)

    def test_review_questions_are_more_likely_to_be_selected(self):
        revision = self.database.revision("Biology")
        candidates = self.database.questions("Biology")
        revision.record(candidates[0], False)
        rng = random.Random(21)
        draws = [revision.choose(candidates, (), rng).key for _ in range(1000)]
        self.assertGreater(draws.count(candidates[0].key), 250)
        self.assertLess(draws.count(candidates[1].key), 100)

    def test_review_picker_does_not_repeat_last_question_immediately(self):
        revision = self.database.revision("General Knowledge")
        candidates = self.database.questions("General Knowledge")
        revision.record(candidates[0], False)
        for seed in range(30):
            chosen = revision.choose(candidates, (candidates[0].key,), random.Random(seed))
            self.assertNotEqual(chosen.key, candidates[0].key)

    def test_times_table_adaptive_generation_is_still_arithmetic(self):
        revision = self.database.revision("Times Tables")
        revision.record(Question(6, 8), False)
        bank = MultiplicationBank(random.Random(2), revision)
        questions = [bank.next_question() for _ in range(60)]
        self.assertTrue(all(question.answer == question.left * question.right for question in questions))
        self.assertGreaterEqual(sum(question.key == Question(6, 8).key for question in questions), 1)

    def test_correct_answer_saved_before_match_is_complete(self):
        duel = Duel(seed=30, topic="Biology", database=self.database)
        question = duel.player_question
        self.assertTrue(duel.submit_answer(str(question.answer)))
        self.assertFalse(duel.finished)
        record = self.database.revision("Biology").get(question.key)
        self.assertEqual(record.correct, 1)
        self.assertEqual(record.attempts, 1)

    def test_existing_regular_bank_remains_without_tracking(self):
        bank = DatabaseBank(self.database, "History", random.Random(2))
        questions = [bank.next_question().question_id for _ in range(16)]
        self.assertEqual(len(set(questions)), 16)

    def test_unseen_questions_get_priority_without_review_queue(self):
        revision = self.database.revision("Biology")
        candidates = self.database.questions("Biology")
        revision.record(candidates[0], True)
        for seed in range(20):
            chosen = revision.choose(candidates, (), random.Random(seed))
            self.assertNotEqual(chosen.key, candidates[0].key)

    def test_legacy_question_database_migrates_without_losing_questions(self):
        legacy_path = Path(self.directory.name) / "older.db"
        with sqlite3.connect(legacy_path) as connection:
            connection.execute("CREATE TABLE questions (id INTEGER PRIMARY KEY, topic TEXT, question TEXT, "
                               "option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT, "
                               "correct_option INTEGER, difficulty INTEGER)")
            connection.execute("INSERT INTO questions VALUES (1, 'Astronomy', 'What is the Sun?', "
                               "'Star', 'Planet', 'Moon', 'Comet', 1, 1)")
        upgraded = QuestionDatabase(legacy_path)
        upgraded.initialise()
        self.assertIn("Astronomy", upgraded.topics())
        self.assertEqual(upgraded.revision("Astronomy").summary.attempts, 0)
        self.assertEqual(upgraded.questions("Astronomy")[0].prompt, "What is the Sun?")

    def test_mastery_status_for_new_question_is_empty(self):
        record = RevisionRecord()
        self.assertEqual(record.priority, 1.0)
        self.assertFalse(record.needs_review)


if __name__ == "__main__":
    unittest.main()
