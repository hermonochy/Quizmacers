import random
import unittest

from quizmancers.combat import AIController, Duel, Wizard
from quizmancers.config import Element, MAX_HEALTH, PROJECTILE_Y
from quizmancers.fusions import FUSION_ELEMENTS, FUSION_WINDOW, FUSIONS, fusion_for, potential_fusions


class FusionTests(unittest.TestCase):
    def wait_for_player(self, duel):
        duel.ai_answer_at = 9999
        duel.ai.familiar_timer = 9999
        duel.player.familiar_timer = 9999
        for _ in range(100):
            if not duel.player_waiting or duel.finished:
                return
            duel.update(0.1)
        self.fail("Spell did not resolve within 10 seconds")

    def correct(self, duel, element):
        self.wait_for_player(duel)
        duel.select_element(element)
        return duel.submit_answer(str(duel.player_question.answer))

    def test_three_fusion_pairs_in_both_orders(self):
        combinations = (
            (Element.FIRE, Element.AIR, "flame_tornado"),
            (Element.FIRE, Element.WATER, "chain_lightning"),
            (Element.EARTH, Element.WATER, "mudslide"),
        )
        self.assertEqual(len(FUSIONS), 3)
        for first, second, expected in combinations:
            for a, b in ((first, second), (second, first)):
                duel = Duel(seed=10)
                self.correct(duel, a)
                self.assertEqual(duel.player.recent_element, a)
                self.correct(duel, b)
                self.assertEqual([shot.fusion for shot in duel.projectiles if shot.fusion], [expected])
                self.assertTrue(any(event.kind == "fusion_cast" for event in duel.pop_events()))

    def test_no_new_controls_required_for_fusion(self):
        duel = Duel(seed=5)
        self.assertFalse(duel.player_fusion_options())
        self.correct(duel, Element.FIRE)
        options = dict(duel.player_fusion_options())
        self.assertEqual(options[Element.AIR].kind, "flame_tornado")
        self.assertEqual(options[Element.WATER].kind, "chain_lightning")
        self.correct(duel, Element.AIR)
        self.assertFalse(duel.player_fusion_options())

    def test_fusion_does_not_repeat_without_a_new_pair(self):
        duel = Duel(seed=9)
        for kind in (Element.FIRE, Element.AIR, Element.AIR, Element.AIR):
            self.correct(duel, kind)
        self.assertEqual(sum(event.kind == "fusion_cast" for event in duel.pop_events()), 1)

    def test_fusion_window_expires_automatically(self):
        duel = Duel(seed=6)
        self.correct(duel, Element.FIRE)
        duel._update_wizard(duel.player, FUSION_WINDOW + 0.05)
        self.assertEqual(duel.player.fusion_window, 0)
        self.assertIsNone(duel.player.recent_element)
        self.correct(duel, Element.AIR)
        self.assertFalse(any(shot.fusion for shot in duel.projectiles))

    def test_incorrect_answer_cancels_primed_fusion(self):
        duel = Duel(seed=14)
        self.correct(duel, Element.FIRE)
        self.wait_for_player(duel)
        self.assertFalse(duel.submit_answer(str(duel.player_question.answer + 1)))
        self.correct(duel, Element.AIR)
        self.assertFalse(any(shot.fusion for shot in duel.projectiles))

    def test_spirit_does_not_form_fusion(self):
        duel = Duel(seed=14)
        self.correct(duel, Element.FIRE)
        self.correct(duel, Element.SPIRIT)
        self.correct(duel, Element.AIR)
        self.assertFalse(any(shot.fusion for shot in duel.projectiles))
        self.assertIsNone(fusion_for(Element.FIRE, Element.SPIRIT))

    def test_fusion_shot_creates_unique_area_and_hit_reaction(self):
        for first, second, name in ((Element.FIRE, Element.AIR, "flame_tornado"),
                                     (Element.FIRE, Element.WATER, "chain_lightning"),
                                     (Element.EARTH, Element.WATER, "mudslide")):
            duel = Duel(seed=12)
            duel.ai.pulse_cooldown = 10
            self.correct(duel, first)
            self.correct(duel, second)
            fusion = next(shot for shot in duel.projectiles if shot.fusion)
            fusion.x = duel.ai.x - 49
            duel.update(0.1)
            self.assertIn(name, [area.kind for area in duel.areas])
            self.assertLess(duel.ai.health, MAX_HEALTH)
            self.assertGreater(duel.ai.hit_remaining, 0)
            self.assertEqual(duel.ai.impact_element, FUSION_ELEMENTS[name])

    def test_fusion_area_damages_over_time(self):
        duel = Duel(seed=12)
        duel.ai.pulse_cooldown = 10
        self.correct(duel, Element.FIRE)
        self.correct(duel, Element.AIR)
        fusion = next(shot for shot in duel.projectiles if shot.fusion)
        fusion.x = duel.ai.x - 49
        duel.update(0.1)
        before = duel.ai.health
        for _ in range(8):
            duel.update(0.1)
        self.assertLess(duel.ai.health, before)

    def test_fusion_scales_with_level(self):
        weak = Duel(seed=7)
        strong = Duel(seed=7, rank_index=8)
        for duel in (weak, strong):
            self.correct(duel, Element.FIRE)
            self.correct(duel, Element.AIR)
        low = next(shot for shot in weak.projectiles if shot.fusion)
        high = next(shot for shot in strong.projectiles if shot.fusion)
        self.assertGreater(high.damage, low.damage)
        self.assertGreater(high.radius, low.radius)

    def test_ai_chooses_fusion_followup(self):
        ai = AIController(random.Random(2))
        wizard = Wizard("ai", 948, recent_element=Element.FIRE, fusion_window=5)
        opponent = Wizard("player", 232)
        choices = [ai.choose_element(wizard, opponent) for _ in range(50)]
        self.assertGreater(sum(kind in (Element.AIR, Element.WATER) for kind in choices), 20)

    def test_fusion_does_not_change_permanent_spell_tier(self):
        duel = Duel(seed=22, rank_index=2)
        self.correct(duel, Element.EARTH)
        self.correct(duel, Element.WATER)
        self.assertEqual(duel.player.level, 1)

    def test_fusion_does_not_increase_controls(self):
        from pathlib import Path
        source = (Path(__file__).parents[1] / "quizmancers" / "game.py").read_text()
        self.assertNotIn("fusion_key", source)


if __name__ == "__main__":
    unittest.main()
