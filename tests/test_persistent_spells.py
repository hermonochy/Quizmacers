from pathlib import Path
from tempfile import TemporaryDirectory
import json
import random
import unittest

from quizmancers.combat import AIController, Duel
from quizmancers.config import Element
from quizmancers.progression import Progress, ProgressStore, appearance_for_rank, save_path, tier_for_rank
from quizmancers.spells import ELEMENT_ORDER, spell_for


class PermanentSpellTests(unittest.TestCase):
    def test_exact_tier_milestones(self):
        self.assertEqual([tier_for_rank(i) for i in range(9)], [1, 1, 1, 2, 2, 2, 3, 3, 4])
        self.assertEqual(Progress(points=20).spell_tier, 1)
        self.assertEqual(Progress(points=80).spell_tier, 4)

    def test_ranks_select_the_right_spells_for_both_wizards(self):
        for index in range(9):
            duel = Duel(seed=8, rank_index=index)
            level = tier_for_rank(index)
            self.assertEqual(duel.player.level, level)
            self.assertEqual(duel.ai.level, level)
            for element in ELEMENT_ORDER:
                self.assertEqual(spell_for(element, duel.player.level), spell_for(element, level))

    def test_many_correct_answers_never_unlock_spells_inside_one_duel(self):
        for rank in (0, 2, 3, 6, 8):
            duel = Duel(seed=1, rank_index=rank)
            start_level = duel.player.level
            for _ in range(27):
                duel.select_element(Element.SPIRIT)
                duel.submit_answer(str(duel.player_question.answer))
            self.assertEqual(duel.player.level, start_level)
            self.assertEqual(duel.ai.level, start_level)

    def test_promotions_and_demotions_change_next_duel_spells(self):
        profile = Progress(points=29)
        self.assertEqual(Duel(rank_index=profile.rank_index).player.level, 1)
        profile.record("player")
        self.assertEqual(Duel(rank_index=profile.rank_index).player.level, 2)
        profile.record("ai")
        self.assertEqual(Duel(rank_index=profile.rank_index).player.level, 1)

    def test_ai_is_quicker_and_more_accurate_at_later_ranks(self):
        beginner = AIController(random.Random(9), rank_index=0)
        expert = AIController(random.Random(9), rank_index=8)
        easy = Duel(seed=12, rank_index=0)
        hard = Duel(seed=12, rank_index=8)
        self.assertLess(expert.next_answer_time(hard.ai, hard.player),
                        beginner.next_answer_time(easy.ai, easy.player))
        low = [beginner.correct(easy.ai, easy.player) for _ in range(2000)]
        high = [expert.correct(hard.ai, hard.player) for _ in range(2000)]
        self.assertGreater(sum(high), sum(low))
        self.assertLess(sum(high) / len(high), 0.9)

    def test_cosmetics_evolve_with_rank(self):
        tiers = [appearance_for_rank(index) for index in range(9)]
        self.assertEqual(tiers[0], 1)
        self.assertEqual(tiers[-1], 4)
        self.assertEqual(tiers, sorted(tiers))

    def test_save_file_is_alongside_game_script(self):
        self.assertEqual(save_path(), Path(__file__).resolve().parents[1] / "progress.json")

    def test_existing_save_keeps_stats_and_tier(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "progress.json"
            path.write_text(json.dumps({"version": 1, "points": 65, "wins": 78,
                                        "losses": 13, "draws": 4}), encoding="utf-8")
            profile = ProgressStore(path).load()
            self.assertEqual((profile.title, profile.spell_tier, profile.wins), ("Magus", 3, 78))
            ProgressStore(path).save(profile)
            self.assertEqual(ProgressStore(path).load(), profile)


if __name__ == "__main__":
    unittest.main()
