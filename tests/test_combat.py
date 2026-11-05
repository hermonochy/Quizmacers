import unittest

from quizmancers.combat import Duel, Projectile
from quizmancers.config import Element, MAX_HEALTH, MAX_SHIELD, QUESTION_SECONDS, ROUND_SECONDS
from quizmancers.questions import MultiplicationBank
from quizmancers.spells import COUNTERS, ELEMENT_ORDER, SPELLBOOK, spell_for


class QuestionTests(unittest.TestCase):
    def test_questions_are_valid_multiplications(self):
        bank = MultiplicationBank()
        for _ in range(100):
            question = bank.next_question()
            self.assertGreaterEqual(question.left, 2)
            self.assertLessEqual(question.left, 12)
            self.assertGreaterEqual(question.right, 2)
            self.assertLessEqual(question.right, 12)
            self.assertEqual(question.answer, question.left * question.right)

    def test_all_elements_have_four_distinct_stages(self):
        self.assertEqual(len(ELEMENT_ORDER), 5)
        for element in ELEMENT_ORDER:
            stages = SPELLBOOK[element]
            self.assertEqual(len(stages), 4)
            self.assertEqual(len({spell.name for spell in stages}), 4)
            self.assertTrue(all(stages[i].power < stages[i + 1].power for i in range(3)))


class DuelTests(unittest.TestCase):
    def correct(self, duel, element=Element.FIRE, elapsed=2.0):
        duel.ai_answer_at = 9999
        duel.ai.familiar_timer = 9999
        duel.player.familiar_timer = 9999
        for _ in range(100):
            if not duel.player_waiting or duel.finished:
                break
            duel.update(0.1)
        duel.player_question_elapsed = elapsed
        duel.select_element(element)
        return duel.submit_answer(str(duel.player_question.answer))

    def projectile(self, owner, element, tier, x, direction, damage=20):
        spec = spell_for(element, tier)
        return Projectile(owner, element, tier, x, 347, direction, spec.travel_speed, damage, spec.radius)

    def test_correct_answer_casts_without_levelling(self):
        duel = Duel(seed=12)
        self.assertTrue(self.correct(duel))
        self.assertEqual(len(duel.projectiles), 1)
        self.assertEqual(duel.projectiles[0].element, Element.FIRE)
        self.assertEqual(duel.player.level, 1)
        self.assertTrue(duel.player_waiting)
        self.assertEqual(duel.player_question_elapsed, 2.0)

    def test_wrong_answer_does_not_cast(self):
        duel = Duel(seed=12)
        self.assertFalse(duel.submit_answer(str(duel.player_question.answer + 1)))
        self.assertEqual(len(duel.projectiles), 0)
        self.assertEqual(duel.player.level, 1)

    def test_invalid_answer_does_not_consume_question(self):
        duel = Duel(seed=12)
        question = duel.player_question
        self.assertIsNone(duel.submit_answer("not an answer"))
        self.assertEqual(duel.player_question, question)

    def test_faster_answer_does_more_damage(self):
        fast = Duel(seed=11)
        slow = Duel(seed=11)
        self.correct(fast, elapsed=1.0)
        self.correct(slow, elapsed=10.0)
        self.assertGreater(fast.projectiles[0].damage, slow.projectiles[0].damage)

    def test_correct_answers_do_not_unlock_spell_levels_in_duel(self):
        duel = Duel(seed=11, rank_index=2)
        for _ in range(16):
            duel.ai.health = MAX_HEALTH
            self.correct(duel)
            self.assertEqual(duel.player.level, 1)
        self.assertEqual(duel.ai.level, 1)

    def test_permanent_rank_affects_every_element_spell(self):
        duel = Duel(seed=7, rank_index=8)
        self.assertEqual(duel.player.level, 4)
        self.assertEqual(duel.ai.level, 4)
        for element in ELEMENT_ORDER:
            duel = Duel(seed=7, rank_index=8)
            self.correct(duel, element)
            if element == Element.SPIRIT:
                self.assertGreater(duel.player.shield, 0)
            else:
                self.assertEqual(duel.projectiles[-1].tier, 4)

    def test_spirit_ward_and_heal_at_later_levels(self):
        duel = Duel(seed=9, rank_index=6)
        duel.player.health = 100
        self.correct(duel, Element.SPIRIT)
        self.assertGreater(duel.player.shield, 0)
        self.assertLessEqual(duel.player.shield, MAX_SHIELD)
        self.assertGreater(duel.player.health, 100)

    def test_spirit_does_not_overheal(self):
        duel = Duel(seed=2, rank_index=8)
        self.correct(duel, Element.SPIRIT)
        self.assertEqual(duel.player.health, MAX_HEALTH)

    def test_shield_absorbs_standard_fireball(self):
        duel = Duel(seed=7)
        duel.ai.shield = 22
        duel.ai.shield_remaining = 7.0
        duel.projectiles.append(self.projectile("player", Element.FIRE, 1, duel.ai.x - 50, 1, 20))
        duel.update(0.1)
        self.assertEqual(duel.ai.health, MAX_HEALTH)
        self.assertEqual(duel.ai.shield, 2)

    def test_air_pierces_shield(self):
        duel = Duel(seed=7)
        duel.ai.shield = MAX_SHIELD
        duel.ai.shield_remaining = 7.0
        duel.projectiles.append(self.projectile("player", Element.AIR, 1, duel.ai.x - 50, 1, 22))
        duel.update(0.1)
        self.assertLess(duel.ai.health, MAX_HEALTH)

    def test_earth_shatters_shield(self):
        fire = Duel(seed=7)
        earth = Duel(seed=7)
        for duel in (fire, earth):
            duel.ai.shield = 60
            duel.ai.shield_remaining = 7.0
        fire.projectiles.append(self.projectile("player", Element.FIRE, 1, fire.ai.x - 50, 1, 20))
        earth.projectiles.append(self.projectile("player", Element.EARTH, 1, earth.ai.x - 50, 1, 20))
        fire.update(0.1)
        earth.update(0.1)
        self.assertLess(earth.ai.shield, fire.ai.shield)

    def test_water_soaks_target_and_extinguishes_burn(self):
        duel = Duel(seed=7)
        duel.ai.burn_remaining = 3.0
        duel.projectiles.append(self.projectile("player", Element.WATER, 1, duel.ai.x - 50, 1, 20))
        duel.update(0.1)
        self.assertEqual(duel.ai.burn_remaining, 0)
        self.assertGreater(duel.ai.soaked_remaining, 0)

    def test_lightning_does_more_damage_to_soaked_target(self):
        wet = Duel(seed=7)
        dry = Duel(seed=7)
        wet.ai.soaked_remaining = 5.0
        for duel in (wet, dry):
            duel.projectiles.append(self.projectile("player", Element.FIRE, 2, duel.ai.x - 50, 1, 30))
            duel.update(0.1)
        self.assertLess(wet.ai.health, dry.ai.health)
        self.assertEqual(wet.ai.soaked_remaining, 0)

    def test_air_cast_clears_casters_soaked_status(self):
        duel = Duel(seed=7)
        duel.player.soaked_remaining = 5.0
        self.correct(duel, Element.AIR)
        self.assertEqual(duel.player.soaked_remaining, 0.0)

    def test_projectile_counters(self):
        for winner_element, loser_element in COUNTERS.items():
            duel = Duel(seed=5)
            duel.projectiles.extend([
                self.projectile("player", winner_element, 1, 560, 1, 23),
                self.projectile("ai", loser_element, 1, 620, -1, 23),
            ])
            duel.update(0.04)
            self.assertEqual(len(duel.projectiles), 1)
            self.assertEqual(duel.projectiles[0].element, winner_element)
            self.assertLess(duel.projectiles[0].damage, 23)
            self.assertTrue(any(event.kind == "clash" for event in duel.pop_events()))

    def test_projectiles_do_not_tunnel_through_each_other(self):
        duel = Duel(seed=5)
        duel.projectiles.extend([
            self.projectile("player", Element.WATER, 2, 555, 1, 25),
            self.projectile("ai", Element.FIRE, 2, 625, -1, 25),
        ])
        duel.update(0.1)
        self.assertEqual(len(duel.projectiles), 1)
        self.assertEqual(duel.projectiles[0].element, Element.WATER)

    def test_simultaneous_hits_can_draw(self):
        duel = Duel(seed=5)
        duel.player.health = 10
        duel.ai.health = 10
        duel.projectiles.extend([
            self.projectile("player", Element.FIRE, 1, duel.ai.x - 50, 1, 20),
            self.projectile("ai", Element.FIRE, 1, duel.player.x + 50, -1, 20),
        ])
        duel.update(0.1)
        self.assertTrue(duel.finished)
        self.assertEqual(duel.winner, "draw")

    def test_hit_causes_visual_reaction_state(self):
        duel = Duel(seed=5)
        duel.projectiles.append(self.projectile("player", Element.EARTH, 1, duel.ai.x - 50, 1, 20))
        duel.update(0.1)
        self.assertGreater(duel.ai.hit_remaining, 0)
        for _ in range(10):
            duel.update(0.1)
        self.assertEqual(duel.ai.hit_remaining, 0)

    def test_questions_expire(self):
        duel = Duel(seed=12)
        for _ in range(186):
            duel.update(0.1)
        self.assertLess(duel.player_question_elapsed, 1.0)
        self.assertTrue(any(event.kind == "timeout" for event in duel.pop_events()))

    def test_ai_answers_without_levelling_in_match(self):
        duel = Duel(seed=12, rank_index=3)
        duel.ai_controller.correct = lambda *args: True
        duel.ai_controller.choose_element = lambda wizard, opponent: Element.FIRE
        for _ in range(80):
            duel.update(0.1)
        self.assertEqual(duel.ai.level, 2)
        self.assertTrue(any(event.kind == "cast" and event.side == "ai" for event in duel.pop_events()))

    def test_match_ends_when_time_expires(self):
        duel = Duel(seed=5)
        duel.elapsed = ROUND_SECONDS - 0.05
        duel.update(0.1)
        self.assertTrue(duel.finished)
        self.assertEqual(duel.winner, "draw")


if __name__ == "__main__":
    unittest.main()
