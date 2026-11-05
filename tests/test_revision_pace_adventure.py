from pathlib import Path
import json
import tempfile
import unittest

from quizmancers.combat import Duel
from quizmancers.config import Element
from quizmancers.pace import PACE_NAMES, pace_for
from quizmancers.settings import GameSettings, SettingsStore
from quizmancers.question_database import QuestionDatabase
from quizmancers.adventure import AdventureWorld, AdventureStore, AdventureProgress


class CorrectionTests(unittest.TestCase):
    def test_first_mistake_gives_short_retry_without_consuming_question(self):
        duel = Duel(seed=5)
        question = duel.player_question
        self.assertFalse(duel.submit_answer(str(question.answer + 1)))
        self.assertFalse(duel.player_waiting)
        self.assertGreater(duel.retry_remaining, 3)
        self.assertIs(duel.player_question, question)
        self.assertEqual(duel.player.combo, 0)
        self.assertTrue(duel.retry_used)

    def test_corrected_answer_still_casts_with_smaller_power(self):
        corrected = Duel(seed=8)
        standard = Duel(seed=8)
        wrong = str(corrected.player_question.answer + 1)
        answer = str(corrected.player_question.answer)
        corrected.player_question_elapsed = 2.0
        standard.player_question_elapsed = 2.0
        corrected.submit_answer(wrong)
        self.assertTrue(corrected.submit_answer(answer))
        self.assertTrue(standard.submit_answer(answer))
        self.assertTrue(corrected.player_waiting)
        self.assertLess(corrected.projectiles[0].damage, standard.projectiles[0].damage)
        self.assertFalse(corrected.retry_remaining)

    def test_second_mistake_ends_question(self):
        duel = Duel(seed=8)
        duel.submit_answer(str(duel.player_question.answer + 1))
        self.assertFalse(duel.submit_answer(str(duel.player_question.answer + 2)))
        self.assertTrue(duel.player_waiting)
        self.assertIn('Correct answer:', duel.player_feedback)

    def test_retry_expires_then_question_is_marked_wrong(self):
        with tempfile.TemporaryDirectory() as folder:
            database = QuestionDatabase(Path(folder) / 'questions.db')
            database.initialise()
            duel = Duel(seed=7, topic='Biology', database=database)
            question = duel.player_question
            duel.ai_answer_at = 9999
            duel.submit_answer('1' if question.answer != 1 else '2')
            for _ in range(50):
                if duel.player_waiting:
                    break
                duel.update(0.1)
            self.assertTrue(duel.player_waiting)
            self.assertEqual(database.revision('Biology').get(question.key).incorrect, 1)

    def test_retry_success_is_still_recorded_for_revision(self):
        with tempfile.TemporaryDirectory() as folder:
            database = QuestionDatabase(Path(folder) / 'questions.db')
            database.initialise()
            duel = Duel(seed=7, topic='Biology', database=database)
            question = duel.player_question
            duel.submit_answer('1' if question.answer != 1 else '2')
            duel.submit_answer(str(question.answer))
            record = database.revision('Biology').get(question.key)
            self.assertEqual(record.attempts, 1)
            self.assertEqual(record.incorrect, 1)
            self.assertEqual(record.correct, 0)
            self.assertTrue(duel.player_waiting)

    def test_correcting_pauses_normal_question_timer(self):
        duel = Duel(seed=3)
        duel.ai_answer_at = 999
        duel.submit_answer(str(duel.player_question.answer + 1))
        old = duel.player_question_elapsed
        duel.update(0.1)
        self.assertEqual(duel.player_question_elapsed, old)


class RevisionPaceTests(unittest.TestCase):
    def test_three_modes_available_and_named(self):
        self.assertEqual(PACE_NAMES, ('Relaxed', 'Standard', 'Competitive'))
        self.assertEqual(pace_for('unknown').name, 'Standard')

    def test_relaxed_more_time_and_ai_slowed(self):
        relaxed = Duel(seed=7, pace='Relaxed')
        standard = Duel(seed=7, pace='Standard')
        competitive = Duel(seed=7, pace='Competitive')
        self.assertGreater(relaxed.question_duration, standard.question_duration)
        self.assertGreater(standard.question_duration, competitive.question_duration)
        self.assertGreater(relaxed.ai_answer_at, standard.ai_answer_at)
        self.assertGreater(standard.ai_answer_at, competitive.ai_answer_at)

    def test_settings_persist_next_to_project_if_requested(self):
        with tempfile.TemporaryDirectory() as folder:
            store = SettingsStore(Path(folder) / 'settings.json')
            store.save(GameSettings('Archmage', 'Relaxed'))
            self.assertEqual(store.load(), GameSettings('Archmage', 'Relaxed'))
            self.assertEqual(json.loads(store.path.read_text())['pace'], 'Relaxed')
            store.path.write_text('{invalid')
            self.assertEqual(store.load(), GameSettings())


class AdventureStructureTests(unittest.TestCase):
    def setUp(self):
        self.world = AdventureWorld()
        self.progress = self.world.new_game()

    def test_school_companion_and_locked_portal_at_start(self):
        self.assertEqual(self.progress.location, 'academy')
        self.assertEqual(self.world.companions[self.progress.companion].name, 'Pip')
        self.assertEqual(self.world.accessible_portals(self.progress), ())
        with self.assertRaises(ValueError):
            self.world.travel(self.progress, 'whisperwood')

    def test_story_crisis_opens_portals_after_school(self):
        for lesson in ('first_wand', 'tables', 'fractions'):
            self.assertTrue(self.world.study(self.progress, lesson, .9))
        self.assertTrue(self.world.encounter(self.progress, 'academy_trial', True))
        story = self.world.story_event(self.progress)
        self.assertIn('Beacon shatters', story)
        self.assertIsNone(self.world.story_event(self.progress))
        self.world.travel(self.progress, 'whisperwood')
        self.assertEqual(self.progress.location, 'whisperwood')
        with self.assertRaises(ValueError):
            self.world.travel(self.progress, 'ember_peaks')

    def test_lessons_require_learning_accuracy_and_training_trial(self):
        self.assertFalse(self.world.study(self.progress, 'first_wand', .2))
        self.assertNotIn('first_wand', self.progress.completed_lessons)
        with self.assertRaises(ValueError):
            self.world.encounter(self.progress, 'academy_trial', True)
        with self.assertRaises(ValueError):
            self.world.study(self.progress, 'fractions', 1.2)

    def test_story_encounters_have_existing_question_filters(self):
        with tempfile.TemporaryDirectory() as folder:
            database = QuestionDatabase(Path(folder) / 'questions.db')
            database.initialise()
            for key in ('first_wand', 'tables', 'fractions', 'algebra', 'academy_trial',
                        'wood_spirit', 'tide_keeper', 'ember_guardian'):
                selection = self.world.study_selection_for(key)
                if selection.is_times_tables:
                    duel = self.world.make_duel(key, database, 0, 'Duelist', 'Relaxed')
                    self.assertTrue(duel.is_times_tables)
                else:
                    self.assertGreater(len(database.questions_for(selection)), 0, key)

    def test_adventure_save_round_trips_independently(self):
        with tempfile.TemporaryDirectory() as folder:
            store = AdventureStore(Path(folder) / 'adventure.json')
            self.progress.completed_lessons.add('tables')
            self.progress.discovered.add('academy')
            store.save(self.progress)
            self.assertEqual(store.load().to_dict(), self.progress.to_dict())
            self.assertIsInstance(AdventureProgress.from_dict(self.progress.to_dict()), AdventureProgress)


if __name__ == '__main__':
    unittest.main()
