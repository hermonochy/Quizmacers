import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from quizmancers.progression import POINTS_PER_RANK, RANKS, Progress, ProgressStore


class RankTests(unittest.TestCase):
    def test_new_player_starts_as_apprentice(self):
        profile = Progress()
        self.assertEqual(profile.points, 0)
        self.assertEqual(profile.title, "Apprentice")
        self.assertEqual(profile.points_to_next, 10)

    def test_each_ten_points_gives_next_title(self):
        for tier, title in enumerate(RANKS):
            with self.subTest(title=title):
                profile = Progress(points=tier * POINTS_PER_RANK)
                self.assertEqual(profile.title, title)
                if tier < len(RANKS) - 1:
                    self.assertEqual(profile.points_to_next, 10)
                    self.assertEqual(profile.rank_progress, 0.0)

    def test_max_title_is_archmage(self):
        self.assertEqual(RANKS[-1], "Archmage")
        profile = Progress(points=80)
        self.assertEqual(profile.title, "Archmage")
        self.assertIsNone(profile.next_title)
        self.assertEqual(profile.rank_progress, 1.0)
        self.assertEqual(profile.points_to_next, 0)
        profile.record("player")
        self.assertEqual(profile.points, 81)
        self.assertEqual(profile.title, "Archmage")

    def test_win_adds_one_point(self):
        profile = Progress(points=5)
        change = profile.record("player")
        self.assertEqual(profile.points, 6)
        self.assertEqual(profile.wins, 1)
        self.assertEqual(change.delta, 1)

    def test_loss_removes_one_point(self):
        profile = Progress(points=5)
        change = profile.record("ai")
        self.assertEqual(profile.points, 4)
        self.assertEqual(profile.losses, 1)
        self.assertEqual(change.delta, -1)

    def test_loss_does_not_make_points_negative(self):
        profile = Progress()
        change = profile.record("ai")
        self.assertEqual(profile.points, 0)
        self.assertEqual(profile.title, "Apprentice")
        self.assertEqual(change.delta, 0)
        self.assertEqual(profile.losses, 1)

    def test_draw_keeps_points_unchanged(self):
        profile = Progress(points=12)
        change = profile.record("draw")
        self.assertEqual(profile.points, 12)
        self.assertEqual(profile.draws, 1)
        self.assertEqual(change.delta, 0)

    def test_rank_up_after_ten_wins(self):
        profile = Progress()
        change = None
        for _ in range(10):
            change = profile.record("player")
        self.assertEqual(profile.title, "Initiate")
        self.assertTrue(change.promoted)
        self.assertEqual(change.old_title, "Apprentice")

    def test_rank_down_when_losing_at_threshold(self):
        profile = Progress(points=10)
        change = profile.record("ai")
        self.assertEqual(profile.title, "Apprentice")
        self.assertTrue(change.demoted)

    def test_progress_within_rank(self):
        profile = Progress(points=17)
        self.assertEqual(profile.title, "Initiate")
        self.assertEqual(profile.next_title, "Novice")
        self.assertEqual(profile.points_to_next, 3)
        self.assertAlmostEqual(profile.rank_progress, 0.7)

    def test_unknown_result_raises_without_modifying_profile(self):
        profile = Progress(points=10)
        with self.assertRaises(ValueError):
            profile.record("nobody")
        self.assertEqual(profile.points, 10)


class SaveTests(unittest.TestCase):
    def test_save_and_reload(self):
        with TemporaryDirectory() as folder:
            store = ProgressStore(Path(folder) / "saves" / "progress.json")
            profile = Progress(points=29, wins=45, losses=16, draws=7)
            store.save(profile)
            reloaded = store.load()
            self.assertEqual(reloaded, profile)
            self.assertEqual(reloaded.title, "Novice")

    def test_latest_result_replaces_previous_save(self):
        with TemporaryDirectory() as folder:
            store = ProgressStore(Path(folder) / "progress.json")
            profile = Progress()
            store.save(profile)
            for _ in range(10):
                profile.record("player")
                store.save(profile)
            self.assertEqual(store.load().title, "Initiate")
            profile.record("ai")
            store.save(profile)
            self.assertEqual(store.load().points, 9)
            self.assertEqual(store.load().title, "Apprentice")

    def test_missing_save_creates_default_player(self):
        with TemporaryDirectory() as folder:
            store = ProgressStore(Path(folder) / "missing.json")
            self.assertEqual(store.load(), Progress())

    def test_broken_save_is_handled(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "progress.json"
            path.write_text('{"points":', encoding="utf-8")
            self.assertEqual(ProgressStore(path).load(), Progress())

    def test_rejects_invalid_values_and_versions(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "progress.json"
            original = Progress().to_dict()
            for change in ({"points": -1}, {"wins": "5"}, {"points": True}, {"version": 999}):
                with self.subTest(change=change):
                    path.write_text(json.dumps({**original, **change}), encoding="utf-8")
                    self.assertEqual(ProgressStore(path).load(), Progress())

    def test_saving_does_not_leave_temp_files(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "progress.json"
            store = ProgressStore(path)
            store.save(Progress(points=10))
            self.assertEqual([p.name for p in Path(folder).iterdir()], ["progress.json"])


if __name__ == "__main__":
    unittest.main()
