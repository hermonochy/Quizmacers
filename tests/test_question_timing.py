from dataclasses import replace
from pathlib import Path
import random
import sqlite3
import tempfile
import unittest

from quizmancers.combat import Duel
from quizmancers.config import Element
from quizmancers.curriculum import StudySelection
from quizmancers.maths_expansion import EXPANDED_MATHS, _quadratic, _binomial
from quizmancers.question_database import QuestionDatabase
from quizmancers.question_timing import ai_solve_delay, round_length_for, time_limit_for
from quizmancers.questions import MultipleChoiceQuestion, Question


class QuestionTimingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = QuestionDatabase(Path(self.temp.name) / 'questions.db')
        self.db.initialise()

    def tearDown(self):
        self.temp.cleanup()

    def test_extended_question_bank_and_courses(self):
        with sqlite3.connect(self.db.path) as db:
            n = db.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
            counts = dict(db.execute("SELECT course, COUNT(*) FROM questions GROUP BY course"))
            bad = db.execute('''SELECT COUNT(*) FROM questions WHERE estimated_seconds IS NULL
                                OR estimated_seconds < 8 OR estimated_seconds > 180''').fetchone()[0]
        self.assertGreaterEqual(n, 800)
        self.assertEqual(bad, 0)
        for course in ('KS1', 'KS2 (SATs)', 'KS3', 'GCSE', 'IGCSE', 'A level'):
            self.assertGreater(counts[course], 100)

    def test_all_generated_answers_are_distinct_and_complete(self):
        self.assertGreaterEqual(len(EXPANDED_MATHS), 500)
        for course, subtopic, prompt, a, b, c, d, seconds in EXPANDED_MATHS:
            self.assertEqual(len({a, b, c, d}), 4, prompt)
            self.assertGreaterEqual(seconds, 15, prompt)
            self.assertLessEqual(len(prompt), 90, prompt)

    def test_quadratic_roots_and_expansions_match_correct_options(self):
        for r1, r2 in ((-4, 7), (-3, -5), (2, 7), (4, 6)):
            prompt, options = _quadratic(r1, r2)
            roots = options[0].replace('x = ', '').split(' or ')
            self.assertEqual({int(v) for v in roots}, {r1, r2})
            self.assertIn('x^2', prompt)
        for a, b in ((-4, 3), (1, -3), (5, 4)):
            prompt, options = _binomial(a, b)
            self.assertIn('Expand', prompt)
            self.assertIn(str(abs(a*b)), options[0])

    def test_quadratic_has_much_more_time_than_recall(self):
        algebra = StudySelection('GCSE', 'AQA', 'Maths', 'Algebra')
        questions = self.db.questions_for(algebra)
        long = next(q for q in questions if q.prompt.startswith('Solve x^2'))
        recall = self.db.questions('Biology')[0]
        self.assertGreaterEqual(long.expected_seconds, 70)
        self.assertGreater(time_limit_for(long), 120)
        self.assertLess(time_limit_for(recall), 65)
        self.assertGreater(time_limit_for(long), 2 * time_limit_for(recall))

    def test_ai_uses_algebra_solving_time_not_times_table_time(self):
        algebra = StudySelection('GCSE', 'AQA', 'Maths', 'Algebra')
        duel = Duel(seed=3, database=self.db, selection=algebra)
        long = next(q for q in duel.bank.questions if q.prompt.startswith('Solve x^2'))
        duel.player_question = long
        duel.ai_question = long
        duel.ai_question_duration = time_limit_for(long)
        duel.question_duration = time_limit_for(long)
        self.assertGreater(duel._ai_answer_delay(), 45)
        times = Duel(seed=3)
        self.assertLess(times._ai_answer_delay(), 9)

    def test_hard_ai_problems_and_player_problems_both_count(self):
        algebra = StudySelection('GCSE', 'AQA', 'Maths', 'Algebra')
        duel = Duel(seed=8, database=self.db, selection=algebra)
        long = next(q for q in duel.bank.questions if q.prompt.startswith('Solve x^2'))
        short = next(q for q in duel.bank.questions if q.prompt.startswith('Solve 2x'))
        duel.player_question = long
        duel.ai_question = short
        self.assertGreater(duel._ai_answer_delay(), 45)
        duel.ai_question = long
        duel.player_question = short
        self.assertGreater(duel._ai_answer_delay(), 45)

    def test_new_questions_recalculate_the_timer(self):
        algebra = StudySelection('GCSE', 'AQA', 'Maths', 'Algebra')
        duel = Duel(seed=8, database=self.db, selection=algebra)
        long = next(q for q in duel.bank.questions if q.prompt.startswith('Solve x^2'))
        duel.bank.next_question = lambda: long
        duel._next_player_question()
        self.assertEqual(duel.question_duration, time_limit_for(long))
        self.assertEqual(duel.player_question_elapsed, 0)
        self.assertGreaterEqual(duel.ai_question_duration, duel.question_duration)

    def test_speed_bonus_scales_with_question_complexity(self):
        algebra = StudySelection('GCSE', 'AQA', 'Maths', 'Algebra')
        duel = Duel(seed=8, database=self.db, selection=algebra)
        long = next(q for q in duel.bank.questions if q.prompt.startswith('Solve x^2'))
        duel.player_question = long
        slower = duel._cast('player', Element.FIRE, 35)
        duel.player_question = replace(long, expected_seconds=12.0)
        faster_expected = duel._cast('player', Element.FIRE, 35)
        self.assertGreater(slower, faster_expected)

    def test_times_tables_unchanged(self):
        duel = Duel(seed=2)
        self.assertIsInstance(duel.player_question, Question)
        self.assertEqual(duel.question_duration, 16.0)
        self.assertEqual(duel.round_duration, 210.0)

    def test_more_thinking_time_for_advanced_duels(self):
        self.assertGreater(round_length_for([80, 80, 80]), 400)
        self.assertEqual(round_length_for([5, 5, 5]), 210)

    def test_question_shuffle_keeps_estimate(self):
        q = MultipleChoiceQuestion(7, 'Solve x^2 - 5x + 6 = 0.', ('x = 2 or 3', 'x = 1 or 6',
                                  'x = -2 or -3', 'x = -1 or -6'), 0, 'Maths', 80.0)
        self.assertEqual(q.shuffle(random.Random(5)).expected_seconds, 80.0)

    def test_custom_timing_and_revision_history_survive_initialise(self):
        selection = StudySelection('GCSE', 'AQA', 'Maths', 'Algebra')
        question = self.db.questions_for(selection)[0]
        self.db.revision_for(selection).record(question, False)
        with sqlite3.connect(self.db.path) as db:
            db.execute('UPDATE questions SET estimated_seconds=135 WHERE id=?', (question.question_id,))
        self.db.initialise()
        questions = self.db.questions_for(selection)
        self.assertEqual(next(q for q in questions if q.question_id == question.question_id).expected_seconds, 135)
        self.assertEqual(self.db.revision_for(selection).get(question.key).incorrect, 1)

    def test_legacy_database_migration_keeps_old_question_ids(self):
        old = Path(self.temp.name) / 'legacy.db'
        with sqlite3.connect(old) as conn:
            conn.execute('''CREATE TABLE questions(id INTEGER PRIMARY KEY,topic TEXT NOT NULL,question TEXT NOT NULL,
                            option_a TEXT NOT NULL, option_b TEXT NOT NULL, option_c TEXT NOT NULL,
                            option_d TEXT NOT NULL, correct_option INTEGER NOT NULL,difficulty INTEGER NOT NULL,
                            UNIQUE(topic,question))''')
            conn.execute("INSERT INTO questions VALUES (42,'Maths::GCSE::Common::Algebra', 'Solve x^2 - 5x + 6 = 0.', 'x = 2 or 3', 'x = 1 or 6', 'x = -2 or -3', 'x = 1 or -6', 1, 1)")
        upgraded = QuestionDatabase(old)
        upgraded.initialise()
        with sqlite3.connect(old) as conn:
            question = conn.execute('SELECT id,estimated_seconds FROM questions WHERE id=42').fetchone()
        self.assertEqual(question[0], 42)
        self.assertGreaterEqual(question[1], 70)


if __name__ == '__main__':
    unittest.main()
