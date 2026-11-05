import random
import sqlite3
import tempfile
import unittest
from pathlib import Path

from quizmancers.combat import Duel
from quizmancers.curriculum import ALL_SUBTOPICS, BOARDS, COURSES, StudySelection
from quizmancers.question_database import QuestionDatabase
from quizmancers.questions import Question


class CurriculumTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.database = QuestionDatabase(Path(self.temporary.name) / "questions.db")
        self.database.initialise()

    def tearDown(self):
        self.temporary.cleanup()

    def test_course_catalog_contains_all_six_levels(self):
        self.assertEqual(self.database.courses(), COURSES)

    def test_board_catalog_is_contextual(self):
        self.assertEqual(self.database.boards("KS1"), ("National Curriculum",))
        self.assertIn("AQA", self.database.boards("GCSE"))
        self.assertIn("Cambridge International", self.database.boards("IGCSE"))
        self.assertIn("OCR B (MEI)", self.database.boards("A level"))

    def test_maths_available_at_every_level(self):
        for course in COURSES:
            with self.subTest(course=course):
                board = BOARDS[course][0]
                self.assertIn("Maths", self.database.subjects(course, board))
                self.assertIn("Times Tables", self.database.subtopics(course, board, "Maths"))

    def test_subtopics_change_with_course(self):
        self.assertIn("Number Bonds", self.database.subtopics("KS1", BOARDS["KS1"][0], "Maths"))
        self.assertIn("Calculus", self.database.subtopics("A level", BOARDS["A level"][0], "Maths"))
        self.assertNotIn("Calculus", self.database.subtopics("KS1", BOARDS["KS1"][0], "Maths"))
        self.assertIn("Fractions", self.database.subtopics("KS2 (SATs)", BOARDS["KS2 (SATs)"][0], "Maths"))

    def test_specific_course_filters_questions(self):
        ks1 = StudySelection("KS1", "National Curriculum", "Maths", "Number Bonds")
        a_level = StudySelection("A level", "AQA", "Maths", "Calculus")
        self.assertTrue(self.database.questions_for(ks1))
        self.assertTrue(self.database.questions_for(a_level))
        self.assertFalse(set(q.key for q in self.database.questions_for(ks1)) &
                         set(q.key for q in self.database.questions_for(a_level)))

    def test_all_subtopics_uses_multiple_question_sets(self):
        selected = StudySelection("GCSE", "AQA", "Maths", ALL_SUBTOPICS)
        self.assertGreater(len(self.database.questions_for(selected)), 25)

    def test_selecting_exam_board_uses_shared_questions(self):
        aqa = StudySelection("GCSE", "AQA", "Maths", "Algebra")
        ocr = StudySelection("GCSE", "OCR", "Maths", "Algebra")
        self.assertEqual({q.key for q in self.database.questions_for(aqa)},
                         {q.key for q in self.database.questions_for(ocr)})

    def test_board_specific_questions_are_isolated(self):
        with sqlite3.connect(self.database.path) as connection:
            connection.execute("""
                INSERT INTO questions
                (topic, course, board, subject, subtopic, question, option_a, option_b, option_c, option_d, correct_option)
                VALUES ('maths_gcse_aqa_extra', 'GCSE', 'AQA', 'Maths', 'Algebra',
                        'Which number is prime here?', '11', '12', '14', '15', 1)
            """)
        aqa = self.database.questions_for(StudySelection("GCSE", "AQA", "Maths", "Algebra"))
        ocr = self.database.questions_for(StudySelection("GCSE", "OCR", "Maths", "Algebra"))
        self.assertIn("Which number is prime here?", [q.prompt for q in aqa])
        self.assertNotIn("Which number is prime here?", [q.prompt for q in ocr])

    def test_new_subject_is_discovered_without_code_change(self):
        with sqlite3.connect(self.database.path) as connection:
            connection.execute("""
                INSERT INTO questions
                (topic, course, board, subject, subtopic, question, option_a, option_b, option_c, option_d, correct_option)
                VALUES ('new_biology', 'GCSE', 'AQA', 'Biology', 'Cell Structure',
                        'What controls the cell?', 'Nucleus', 'Vacuole', 'Wall', 'Ribosome', 1)
            """)
        self.assertIn("Biology", self.database.subjects("GCSE", "AQA"))
        self.assertEqual(self.database.subtopics("GCSE", "AQA", "Biology"), ("Cell Structure",))
        duel = Duel(seed=9, database=self.database,
                    selection=StudySelection("GCSE", "AQA", "Biology", "Cell Structure"))
        self.assertEqual(duel.player_question.prompt, "What controls the cell?")

    def test_revision_shared_across_all_and_specific_subtopic(self):
        exact = StudySelection("GCSE", "AQA", "Maths", "Algebra")
        broad = StudySelection("GCSE", "AQA", "Maths", ALL_SUBTOPICS)
        question = self.database.questions_for(exact)[0]
        self.database.revision_for(exact).record(question, False)
        self.assertTrue(self.database.revision_for(broad).get(question.key).needs_review)
        self.assertEqual(self.database.revision_summary_for(exact).to_review, 1)
        self.assertEqual(self.database.revision_summary_for(broad).to_review, 1)

    def test_revision_is_separate_by_course_and_board(self):
        aqa = StudySelection("GCSE", "AQA", "Maths", "Algebra")
        ocr = StudySelection("GCSE", "OCR", "Maths", "Algebra")
        self.database.revision_for(aqa).record(self.database.questions_for(aqa)[0], False)
        self.assertEqual(self.database.revision_summary_for(aqa).to_review, 1)
        self.assertEqual(self.database.revision_summary_for(ocr).to_review, 0)

    def test_ks1_tables_are_appropriate(self):
        selected = StudySelection("KS1", "National Curriculum", "Maths", "Times Tables")
        duel = Duel(seed=24, database=self.database, selection=selected)
        for _ in range(90):
            question = duel.bank.next_question()
            self.assertIsInstance(question, Question)
            self.assertTrue(question.left in (2, 5, 10) or question.right in (2, 5, 10))
            self.assertLessEqual(max(question.left, question.right), 10)

    def test_existing_times_tables_revision_history_is_reused(self):
        q = Question(7, 8)
        self.database.revision("Times Tables").record(q, False)
        selected = StudySelection("KS2 (SATs)", "National Curriculum", "Maths", "Times Tables")
        self.assertTrue(self.database.revision_for(selected).get(q.key).needs_review)

    def test_old_non_maths_topics_migrate_to_ks3(self):
        biology = StudySelection("KS3", "National Curriculum", "Biology", "General")
        self.assertEqual(len(self.database.questions_for(biology)), 16)
        self.assertEqual(self.database.revision_for(biology).topic, "Biology")

    def test_legacy_database_migration_keeps_answers_and_review(self):
        location = Path(self.temporary.name) / "older.db"
        with sqlite3.connect(location) as connection:
            connection.execute("""
                CREATE TABLE questions (
                    id INTEGER PRIMARY KEY, topic TEXT, question TEXT,
                    option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT,
                    correct_option INTEGER, difficulty INTEGER, UNIQUE(topic, question)
                )
            """)
            connection.execute("INSERT INTO questions VALUES (400, 'Music', 'How many notes in C major?', '7', '6', '8', '5', 1, 1)")
            connection.execute("""
                CREATE TABLE revision_progress (
                    topic TEXT NOT NULL, question_key TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
                    correct INTEGER NOT NULL DEFAULT 0, incorrect INTEGER NOT NULL DEFAULT 0,
                    timeouts INTEGER NOT NULL DEFAULT 0, streak INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(topic, question_key))
            """)
            connection.execute("INSERT INTO revision_progress VALUES ('Music', 'db:400', 2, 1, 1, 0, 0)")
        upgraded = QuestionDatabase(location)
        upgraded.initialise()
        music = StudySelection("KS3", "National Curriculum", "Music", "General")
        self.assertEqual(upgraded.questions_for(music)[0].question_id, 400)
        self.assertEqual(upgraded.revision_for(music).get("db:400").attempts, 2)

    def test_all_sample_answers_are_unique_and_valid(self):
        with sqlite3.connect(self.database.path) as connection:
            rows = connection.execute("SELECT option_a,option_b,option_c,option_d,correct_option FROM questions").fetchall()
        for a, b, c, d, correct in rows:
            self.assertEqual(len({a,b,c,d}), 4)
            self.assertEqual(correct, 1)

    def test_initialise_does_not_duplicate_or_reset_edits(self):
        with sqlite3.connect(self.database.path) as connection:
            connection.execute("UPDATE questions SET option_b='Custom answer' WHERE id=1")
            total = connection.execute("SELECT count(*) FROM questions").fetchone()[0]
        self.database.initialise()
        with sqlite3.connect(self.database.path) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM questions").fetchone()[0], total)
            self.assertEqual(connection.execute("SELECT option_b FROM questions WHERE id=1").fetchone()[0], 'Custom answer')


if __name__ == "__main__":
    unittest.main()
