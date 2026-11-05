import ast
from pathlib import Path
import unittest

from quizmancers.combat import Duel
from quizmancers.progression import Progress


class MenuStartupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).parents[1] / "quizmancers" / "game.py").read_text()
        cls.tree = ast.parse(cls.source)

    def test_game_initialises_on_menu(self):
        self.assertIn('self.phase = "menu"', self.source)

    def test_new_match_uses_saved_rank(self):
        self.assertIn("rank_index=self.progress.rank_index", self.source)

    def test_round_time_does_not_start_before_first_duel_update(self):
        duel = Duel(rank_index=3)
        self.assertEqual(duel.elapsed, 0)
        self.assertEqual(duel.ai_question_elapsed, 0)
        self.assertEqual(duel.player_question_elapsed, 0)
        self.assertEqual(duel.projectiles, [])

    def test_game_advances_duel_only_when_playing(self):
        methods = {method.name: method for node in self.tree.body if isinstance(node, ast.ClassDef)
                   and node.name == "Game" for method in node.body if isinstance(method, ast.FunctionDef)}
        run = methods["run"]
        decision = next(node for node in ast.walk(run) if isinstance(node, ast.If)
                        and isinstance(node.test, ast.BoolOp)
                        and any(isinstance(value, ast.Compare) and isinstance(value.left, ast.Attribute)
                                and value.left.attr == "phase" for value in node.test.values)
                        and any(isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute)
                                and item.func.attr == "update" for item in ast.walk(node)))
        self.assertIn("playing", ast.unparse(decision.test))

    def test_early_answer_is_rejected(self):
        methods = {method.name: method for node in self.tree.body if isinstance(node, ast.ClassDef)
                   and node.name == "Game" for method in node.body if isinstance(method, ast.FunctionDef)}
        submit = ast.unparse(methods["_submit"])
        self.assertIn('self.phase != \'playing\'', submit)


if __name__ == "__main__":
    unittest.main()
