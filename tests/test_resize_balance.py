import random
import unittest

from quizmancers.combat import AIController, Duel, Wizard
from quizmancers.config import WIDTH, HEIGHT, Element
from quizmancers.viewport import Viewport


class ViewportTests(unittest.TestCase):
    def test_native_resolution(self):
        view = Viewport(WIDTH, HEIGHT, WIDTH, HEIGHT)
        self.assertEqual(view.size, (WIDTH, HEIGHT))
        self.assertEqual(view.origin, (0, 0))
        self.assertEqual(view.to_virtual((WIDTH // 2, HEIGHT // 2)), (WIDTH // 2, HEIGHT // 2))

    def test_wider_window_adds_side_bars(self):
        view = Viewport(WIDTH, HEIGHT, 1600, 720)
        self.assertEqual(view.size, (1180, 720))
        self.assertEqual(view.origin, (210, 0))
        self.assertIsNone(view.to_virtual((10, 360)))
        self.assertEqual(view.to_virtual((210, 0)), (0, 0))
        self.assertEqual(view.to_virtual((800, 360)), (590, 360))

    def test_taller_window_adds_top_bottom_bars(self):
        view = Viewport(WIDTH, HEIGHT, 1180, 1000)
        self.assertEqual(view.origin, (0, 140))
        self.assertIsNone(view.to_virtual((500, 80)))
        self.assertEqual(view.to_virtual((500, 140)), (500, 0))
        self.assertIsNone(view.to_virtual((500, 900)))

    def test_half_size_transforms_mouse_clicks(self):
        view = Viewport(WIDTH, HEIGHT, 590, 360)
        self.assertEqual(view.size, (590, 360))
        self.assertEqual(view.to_virtual((150, 322)), (300, 644))
        self.assertEqual(view.to_virtual((250, 300)), (500, 600))

    def test_resize_preserves_virtual_game_area(self):
        for width, height in ((900, 550), (1920, 1080), (700, 700), (2560, 800)):
            view = Viewport(WIDTH, HEIGHT, width, height)
            x, y = view.origin
            w, h = view.size
            self.assertLessEqual(x + w, width)
            self.assertLessEqual(y + h, height)
            midpoint = view.to_virtual((x + w // 2, y + h // 2))
            self.assertAlmostEqual(midpoint[0], WIDTH // 2, delta=2)
            self.assertAlmostEqual(midpoint[1], HEIGHT // 2, delta=2)


class BalanceTests(unittest.TestCase):
    def test_ai_uses_same_spell_tier_as_player(self):
        for rank in (0, 2, 3, 5, 6, 7, 8):
            duel = Duel(seed=5, rank_index=rank)
            self.assertEqual(duel.ai.level, duel.player.level)

    def test_ai_still_gets_faster_as_opponent_levels(self):
        novice = AIController(random.Random(3))
        advanced = AIController(random.Random(3))
        rival = Wizard("ai", 900, level=1)
        self.assertLess(advanced.next_answer_time(rival, Wizard("player", 200, level=4)),
                        novice.next_answer_time(rival, Wizard("player", 200, level=1)))

    def test_default_ai_answer_rate_is_below_ninety_percent_at_max_level(self):
        controller = AIController(random.Random(5))
        rival = Wizard("ai", 900, level=4)
        player = Wizard("player", 200, level=4)
        results = [controller.correct(rival, player) for _ in range(1000)]
        self.assertLess(sum(results), 910)
        self.assertGreater(sum(results), 830)

    def test_speed_and_accuracy_can_beat_default_ai_without_parries(self):
        wins = 0
        for seed in range(24):
            duel = Duel(seed=seed * 3 + 2)
            answer_timer = 1.9
            for _ in range(1150):
                if duel.player_question_elapsed >= answer_timer:
                    duel.select_element(Element.FIRE)
                    duel.submit_answer(str(duel.player_question.answer))
                duel.update(0.1)
                duel.pop_events()
                if duel.finished:
                    break
            wins += duel.winner == "player"
        self.assertGreaterEqual(wins, 20)


if __name__ == "__main__":
    unittest.main()
