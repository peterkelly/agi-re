import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("render_playthrough_graph", ROOT / "tools/render_playthrough_graph.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class PlaythroughGraphTest(unittest.TestCase):
    def test_sq122_graph_validates_and_totals_202(self):
        path = ROOT / "docs/src/games/sq1_22_success_path.json"
        data = MODULE.load_graph(path)
        self.assertEqual(202, sum(data["nodes"][[n["id"] for n in data["nodes"]].index(node_id)]["score_delta"] for node_id in data["score_route"]))
        self.assertEqual(45, len(data["score_route"]))

    def test_dot_contains_random_retry_loops(self):
        data = MODULE.load_graph(ROOT / "docs/src/games/sq1_22_success_path.json")
        dot = MODULE.to_dot(data)
        self.assertIn("rankdir=TB", dot)
        self.assertIn('"rng_ship" -> "rng_ship"', dot)
        self.assertIn('"rng_question" -> "rng_question"', dot)


if __name__ == "__main__":
    unittest.main()
