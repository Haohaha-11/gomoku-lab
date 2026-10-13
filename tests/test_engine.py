"""Regression tests for game rules, matched search trees, and timeout safety."""
import copy
import random
import unittest

from gomoku.engine import candidate_moves, evaluate, search, validate_board, winner, winning_cells


def board(size=9):
    return [[0] * size for _ in range(size)]


class RulesTests(unittest.TestCase):
    def test_all_directions_and_edges(self):
        for start, direction in [((0, 0), (0, 1)), ((0, 8), (1, 0)),
                                 ((0, 0), (1, 1)), ((0, 8), (1, -1))]:
            with self.subTest(direction=direction):
                position = board()
                for i in range(6):
                    position[start[0] + i * direction[0]][start[1] + i * direction[1]] = 2
                self.assertEqual(winner(position), 2)
                self.assertEqual(len(winning_cells(position)), 6)

    def test_invalid_board(self):
        for position in [[], [[0] * 5] * 4, [[True] * 5] * 5, [[3] * 5] * 5]:
            with self.assertRaises(ValueError):
                validate_board(position)

    def test_terminal_and_full_board(self):
        position = board()
        position[0][:5] = [1] * 5
        for algorithm in ("minimax", "alphabeta"):
            result = search(position, 2, algorithm)
            self.assertIsNone(result["move"])
            self.assertEqual(result["score_kind"], "terminal")
            self.assertLess(result["score"], 0)
        # This filled 5×5 pattern has no monochrome horizontal, vertical or diagonal five.
        full = [[1, 1, 2, 2, 1], [2, 2, 1, 1, 2], [1, 1, 2, 2, 1],
                [2, 2, 1, 1, 2], [1, 2, 1, 2, 1]]
        self.assertEqual(winner(full), 0)
        self.assertIsNone(search(full, 1)["move"])
        full[4][4] = 0
        result = search(full, 1, depth=1, time_limit_ms=None)
        self.assertEqual(result["move"], [4, 4])
        self.assertEqual(result["score"], 0)


class SearchTests(unittest.TestCase):
    def test_upstream_patterns_are_used_and_zero_sum(self):
        position = board()
        position[4][2:6] = [1, 1, 0, 1]
        self.assertGreaterEqual(evaluate(position, 1), 1000)
        self.assertEqual(evaluate(position, 1), -evaluate(position, 2))

    def test_immediate_win_and_unique_block(self):
        for algorithm in ("minimax", "alphabeta"):
            position = board()
            position[0][:4] = [1] * 4
            position[1][0] = 2
            self.assertEqual(search(position, 1, algorithm, 1, 10, None)["move"], [0, 4])
            position[0][:4] = [2] * 4
            position[1][0] = 1
            self.assertEqual(search(position, 1, algorithm, 1, 10, None)["move"], [0, 4])

    def test_forced_moves_survive_cap(self):
        position = board()
        position[4][2:6] = [2] * 4
        moves = candidate_moves(position, 1, 1)
        self.assertIn((4, 1), moves)
        self.assertIn((4, 6), moves)
        self.assertEqual(len(moves), 2)

    def test_legal_timeout_and_board_restoration(self):
        position = board(15)
        position[7][7] = 1
        before = copy.deepcopy(position)
        result = search(position, 2, "minimax", 6, 16, 1)
        self.assertTrue(result["timeout"])
        self.assertLess(result["completed_depth"], 6)
        r, c = result["move"]
        self.assertEqual(position[r][c], 0)
        self.assertEqual(position, before)
        if result["completed_depth"] == 0:
            self.assertEqual(result["score_kind"], "fallback")

    def test_matched_algorithms_seeded_positions(self):
        rng = random.Random(20261013)
        for size in (9, 13, 15):
            for sample in range(2):
                position = board(size)
                middle = size // 2
                cells = [(r, c) for r in range(middle - 2, middle + 3)
                         for c in range(middle - 2, middle + 3)]
                for i, (r, c) in enumerate(rng.sample(cells, 8)):
                    position[r][c] = i % 2 + 1
                self.assertEqual(winner(position), 0)
                before = copy.deepcopy(position)
                for depth in (1, 2, 3):
                    with self.subTest(size=size, sample=sample, depth=depth):
                        mm = search(position, 1, "minimax", depth, 5, None)
                        ab = search(position, 1, "alphabeta", depth, 5, None)
                        self.assertEqual((mm["score"], mm["move"]), (ab["score"], ab["move"]))
                        self.assertEqual(ab["completed_depth"], depth)
                        self.assertLessEqual(ab["nodes"], mm["nodes"])
                        self.assertEqual(position, before)

    def test_empty_board_and_trace(self):
        result = search(board(), 1, "alphabeta", 3, 6, None)
        self.assertEqual(result["move"], [4, 4])
        ids = {node["id"] for node in result["tree"]["nodes"]}
        self.assertTrue(all(node["parent"] in ids or node["parent"] is None
                            for node in result["tree"]["nodes"]))
        self.assertEqual(result["tree"]["depth"], 3)
        self.assertTrue(all(c["bound"] in ("exact", "upper_bound") for c in result["candidates"]))


if __name__ == "__main__":
    unittest.main()
