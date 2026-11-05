import random
import unittest

from quizmancers.combat import AIController, Duel, Projectile, Wizard
from quizmancers.config import Element, MAX_HEALTH, MAX_SHIELD, PROJECTILE_Y
from quizmancers.spells import spell_for


class AscensionTests(unittest.TestCase):
    def duel_at_level(self, level, seed=24):
        rank_for_tier = {1: 0, 2: 3, 3: 6, 4: 8}
        return Duel(seed=seed, rank_index=rank_for_tier[level])

    def cast(self, duel, element):
        duel.select_element(element)
        return duel.submit_answer(str(duel.player_question.answer))

    def move_main_to_hit(self, duel):
        for shot in duel.projectiles:
            shot.x = duel.ai.x - 49
        duel.update(0.1)

    def test_fire_3_generates_multiple_lightning_bolts(self):
        duel = self.duel_at_level(3)
        self.cast(duel, Element.FIRE)
        self.assertEqual(len(duel.projectiles), 1)
        self.assertEqual(len(duel.delayed), 2)
        self.assertGreater(duel.delayed[1].delay, duel.delayed[0].delay)
        for _ in range(8):
            duel.update(0.1)
        self.assertGreaterEqual(len(duel.projectiles), 2)

    def test_fire_4_creates_inferno_after_impact(self):
        duel = self.duel_at_level(4)
        self.cast(duel, Element.FIRE)
        self.move_main_to_hit(duel)
        self.assertTrue(any(area.kind == "inferno" for area in duel.areas))
        health = duel.ai.health
        for _ in range(9):
            duel.update(0.1)
        self.assertLess(duel.ai.health, health)

    def test_earth_3_creates_quake_zone(self):
        duel = self.duel_at_level(3)
        self.cast(duel, Element.EARTH)
        self.move_main_to_hit(duel)
        self.assertEqual(duel.areas[0].kind, "quake")

    def test_earth_4_creates_falling_rocks(self):
        duel = self.duel_at_level(4)
        self.cast(duel, Element.EARTH)
        self.move_main_to_hit(duel)
        self.assertEqual(duel.areas[0].kind, "cataclysm")

    def test_water_3_and_4_have_distinct_areas(self):
        expected = {3: "surge", 4: "maelstrom"}
        for tier, name in expected.items():
            duel = self.duel_at_level(tier)
            self.cast(duel, Element.WATER)
            self.move_main_to_hit(duel)
            self.assertEqual(duel.areas[0].kind, name)
            self.assertGreater(duel.ai.soaked_remaining, 0)

    def test_air_3_spawns_cyclone(self):
        duel = self.duel_at_level(3)
        self.cast(duel, Element.AIR)
        self.move_main_to_hit(duel)
        self.assertEqual(duel.areas[0].kind, "cyclone")

    def test_air_4_has_three_extra_projectiles(self):
        duel = self.duel_at_level(4)
        self.cast(duel, Element.AIR)
        self.assertEqual(len(duel.delayed), 3)
        self.assertEqual([cast.phase for cast in duel.delayed], [1, 2, 3])

    def test_spirit_3_heals_over_time(self):
        duel = self.duel_at_level(3)
        duel.player.health = 110
        self.cast(duel, Element.SPIRIT)
        first = duel.player.health
        for _ in range(11):
            duel.update(0.1)
        self.assertGreater(duel.player.health, first)
        self.assertGreater(duel.player.bloom_remaining, 0)

    def test_spirit_4_reflects_first_spell(self):
        duel = self.duel_at_level(4)
        self.cast(duel, Element.SPIRIT)
        old_health = duel.player.health
        duel.projectiles.append(Projectile("ai", Element.FIRE, 1, duel.player.x + 49,
                                           PROJECTILE_Y, -1, 535, 25, 14))
        duel.update(0.1)
        self.assertEqual(duel.player.health, old_health)
        self.assertEqual(duel.player.sanctuary_charges, 0)
        self.assertTrue(any(shot.reflected for shot in duel.projectiles))
        self.assertTrue(any(event.kind == "parry" for event in duel.pop_events()))


class FlowTests(unittest.TestCase):
    def test_automatic_familiar_attacks_during_question(self):
        duel = Duel(seed=12)
        for _ in range(50):
            duel.update(0.1)
        self.assertTrue(any(event.kind == "familiar" and event.side == "player"
                            for event in duel.pop_events()))
        self.assertEqual(duel.player.level, 1)
        self.assertGreater(duel.player_question_elapsed, 1.0)

    def test_player_parry_blocks_spell_and_has_cooldown(self):
        duel = Duel(seed=15)
        self.assertTrue(duel.activate_pulse("player"))
        self.assertFalse(duel.activate_pulse("player"))
        duel.projectiles.append(Projectile("ai", Element.EARTH, 1, duel.player.x + 49,
                                           PROJECTILE_Y, -1, 415, 30, 15))
        duel.update(0.1)
        self.assertEqual(duel.player.health, MAX_HEALTH)
        self.assertTrue(any(event.kind == "parry" for event in duel.pop_events()))
        self.assertGreater(duel.player.pulse_cooldown, 0)

    def test_combo_boosts_correct_answer_damage(self):
        low = Duel(seed=9)
        high = Duel(seed=9)
        high.player.combo = 4
        low.player_question_elapsed = high.player_question_elapsed = 2.0
        low.submit_answer(str(low.player_question.answer))
        high.submit_answer(str(high.player_question.answer))
        self.assertGreater(high.projectiles[0].damage, low.projectiles[0].damage)
        high.ai_answer_at = 999
        high.ai.familiar_timer = 999
        high.player.familiar_timer = 999
        for _ in range(100):
            if not high.player_waiting:
                break
            high.update(0.1)
        high.submit_answer(str(high.player_question.answer + 1))
        self.assertEqual(high.player.combo, 0)

    def test_ai_gets_faster_when_player_levels_up(self):
        beginner = AIController(random.Random(8))
        evolved = AIController(random.Random(8))
        novice = Wizard("player", 200, level=1)
        expert = Wizard("player", 200, level=4)
        rival = Wizard("ai", 900, level=1)
        self.assertLess(evolved.next_answer_time(rival, expert),
                        beginner.next_answer_time(rival, novice))

    def test_ai_starts_at_the_players_permanent_spell_tier(self):
        duel = Duel(seed=11, rank_index=8)
        duel.update(0.1)
        self.assertEqual(duel.player.level, 4)
        self.assertEqual(duel.ai.level, 4)

    def test_difficulty_presets_change_ai_thinking_time(self):
        player = Wizard("player", 232, level=2)
        rival = Wizard("ai", 948, level=2)
        slow = AIController(random.Random(8), "Apprentice")
        normal = AIController(random.Random(8), "Duelist")
        fast = AIController(random.Random(8), "Archmage")
        self.assertGreater(slow.next_answer_time(rival, player), normal.next_answer_time(rival, player))
        self.assertGreater(normal.next_answer_time(rival, player), fast.next_answer_time(rival, player))

    def test_switching_difficulty_updates_ai(self):
        duel = Duel(seed=8)
        duel.set_difficulty("Archmage")
        self.assertEqual(duel.ai_controller.difficulty, "Archmage")
        duel.set_difficulty("invalid")
        self.assertEqual(duel.difficulty, "Archmage")

    def test_projectiles_continue_while_question_is_open(self):
        duel = Duel(seed=4)
        start = duel.player_question
        duel._launch("player", Element.WATER, 2, 25)
        initial_x = duel.projectiles[0].x
        duel.update(0.1)
        self.assertGreater(duel.projectiles[0].x, initial_x)
        self.assertEqual(duel.player_question, start)

    def test_familiar_does_not_apply_full_elemental_status(self):
        duel = Duel(seed=10)
        duel._launch("player", Element.WATER, 4, 8, familiar=True)
        duel.projectiles[-1].x = duel.ai.x - 49
        duel.update(0.1)
        self.assertEqual(duel.ai.soaked_remaining, 0)


if __name__ == "__main__":
    unittest.main()
