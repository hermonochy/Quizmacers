import random
import sqlite3
import tempfile
import unittest
from pathlib import Path

from quizmancers.combat import Duel
from quizmancers.config import Element, MAX_HEALTH
from quizmancers.question_data import SEED_QUESTIONS
from quizmancers.question_database import DatabaseBank, QuestionDatabase
from quizmancers.questions import MultipleChoiceQuestion, Question


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database = QuestionDatabase(Path(self.directory.name) / "test_questions.db")
        self.database.initialise()

    def tearDown(self):
        self.directory.cleanup()

    def test_topics_and_sample_questions_are_in_sqlite(self):
        topics = self.database.topics()
        self.assertEqual(len(topics), 9)
        self.assertEqual(topics[0], "Times Tables")
        self.assertEqual(len(SEED_QUESTIONS), 8)
        with sqlite3.connect(self.database.path) as connection:
            total = connection.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
            indexes = connection.execute("PRAGMA index_list(questions)").fetchall()
        self.assertGreaterEqual(total, 800)
        self.assertTrue(indexes)

    def test_each_topic_is_distinct_and_answer_keys_work(self):
        for topic in self.database.topics()[1:]:
            bank = DatabaseBank(self.database, topic, random.Random(22))
            question = bank.next_question()
            self.assertIsInstance(question, MultipleChoiceQuestion)
            self.assertEqual(question.topic, topic)
            self.assertEqual(len(set(question.options)), 4)
            self.assertTrue(question.is_correct(str(question.answer)))
            for option in range(1, 5):
                if option != question.answer:
                    self.assertFalse(question.is_correct(str(option)))

    def test_all_options_remain_correct_when_shuffled(self):
        bank = DatabaseBank(self.database, "Computing", random.Random(4))
        question = bank.next_question()
        correct = question.options[question.correct_index]
        for seed in range(30):
            shuffled = question.shuffle(random.Random(seed))
            self.assertEqual(correct, shuffled.options[shuffled.correct_index])

    def test_question_pool_avoids_repeating_an_unseen_question(self):
        bank = DatabaseBank(self.database, "Physics", random.Random(6))
        questions = [bank.next_question().question_id for _ in range(16)]
        self.assertEqual(len(set(questions)), 16)

    def test_user_added_topic_is_visible_without_code_changes(self):
        with sqlite3.connect(self.database.path) as connection:
            connection.execute("""
                INSERT INTO questions
                (topic, question, option_a, option_b, option_c, option_d, correct_option)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("Astronomy", "Which star is closest to Earth?", "The Sun", "Sirius", "Vega", "Polaris", 1))
        self.database.initialise()
        self.assertIn("Astronomy", self.database.topics())
        question = DatabaseBank(self.database, "Astronomy").next_question()
        self.assertIn("The Sun", question.options)

    def test_database_edits_are_not_overwritten(self):
        with sqlite3.connect(self.database.path) as connection:
            connection.execute("UPDATE questions SET option_b = ? WHERE id = 1", ("Edited choice",))
        self.database.initialise()
        with sqlite3.connect(self.database.path) as connection:
            row = connection.execute("SELECT option_b FROM questions WHERE id = 1").fetchone()
        self.assertEqual(row[0], "Edited choice")

    def test_times_tables_still_generated_without_db_topic(self):
        duel = Duel(seed=21, database=self.database)
        self.assertEqual(duel.topic, "Times Tables")
        self.assertIsInstance(duel.player_question, Question)
        self.assertEqual(duel.player_question.answer, duel.player_question.left * duel.player_question.right)


class PacingTests(unittest.TestCase):
    def test_correct_spell_holds_question_until_impact(self):
        duel = Duel(seed=12)
        duel.ai_answer_at = 500
        duel.ai.familiar_timer = 999
        duel.player.familiar_timer = 999
        old = duel.player_question
        self.assertTrue(duel.submit_answer(str(old.answer)))
        self.assertTrue(duel.player_waiting)
        self.assertIs(duel.player_question, old)
        self.assertIsNone(duel.submit_answer(str(old.answer)))
        previous_time = duel.player_question_elapsed
        for _ in range(4):
            duel.update(0.1)
        self.assertIs(duel.player_question, old)
        self.assertEqual(duel.player_question_elapsed, previous_time)
        for _ in range(70):
            duel.update(0.1)
            if not duel.player_waiting:
                break
        self.assertFalse(duel.player_waiting)
        self.assertIsNot(duel.player_question, old)
        self.assertEqual(duel.player_question_elapsed, 0)
        self.assertLess(duel.ai.health, MAX_HEALTH)

    def test_wrong_answer_fizzles_and_gives_short_pause(self):
        duel = Duel(seed=20)
        old = duel.player_question
        self.assertFalse(duel.submit_answer(str(old.answer + 1)))
        self.assertIs(duel.player_question, old)
        for _ in range(10):
            duel.update(0.1)
        self.assertIs(duel.player_question, old)
        self.assertIn(str(old.answer), duel.player_feedback)
        for _ in range(14):
            duel.update(0.1)
        self.assertIsNot(duel.player_question, old)

    def test_spirit_spell_has_a_visible_delay_without_a_projectile(self):
        duel = Duel(seed=21)
        duel.select_element(Element.SPIRIT)
        old = duel.player_question
        self.assertTrue(duel.submit_answer(str(old.answer)))
        for _ in range(5):
            duel.update(0.1)
        self.assertIs(duel.player_question, old)
        for _ in range(7):
            duel.update(0.1)
        self.assertIsNot(duel.player_question, old)

    def test_ai_waits_for_projectile_resolution_too(self):
        duel = Duel(seed=8)
        duel.ai_controller.correct = lambda *args: True
        duel.ai_controller.choose_element = lambda *args: Element.FIRE
        duel.ai_answer_at = 0.1
        duel.update(0.1)
        old = duel.ai_question
        self.assertTrue(duel.ai_waiting)
        duel.update(0.1)
        self.assertIs(duel.ai_question, old)
        for _ in range(60):
            duel.update(0.1)
            if not duel.ai_waiting:
                break
        self.assertIsNot(duel.ai_question, old)

    def test_new_topic_uses_clickable_choices_and_more_reading_time(self):
        with tempfile.TemporaryDirectory() as directory:
            database = QuestionDatabase(Path(directory) / "questions.db")
            database.initialise()
            duel = Duel(seed=5, topic="Biology", database=database)
            self.assertEqual(duel.topic, "Biology")
            self.assertGreater(duel.question_duration, Duel(seed=5).question_duration)
            self.assertIsNone(duel.submit_answer("5"))
            self.assertTrue(duel.submit_answer(str(duel.player_question.answer)))
            self.assertTrue(duel.player_waiting)

    def test_level_three_salvo_waits_for_all_projectiles(self):
        duel = Duel(seed=7, rank_index=6)
        duel.ai_answer_at = 500
        duel.player.familiar_timer = 999
        duel.ai.familiar_timer = 999
        duel.select_element(Element.FIRE)
        old = duel.player_question
        self.assertTrue(duel.submit_answer(str(old.answer)))
        self.assertEqual(len(duel.delayed), 2)
        for _ in range(7):
            duel.update(0.1)
        self.assertTrue(duel.player_waiting)
        for _ in range(70):
            duel.update(0.1)
            if not duel.player_waiting:
                break
        self.assertFalse(duel.player_waiting)
        self.assertIsNot(duel.player_question, old)


if __name__ == "__main__":
    unittest.main()
