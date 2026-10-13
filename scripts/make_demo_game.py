"""Create a legal scripted opening + genuine engine continuation for video replay."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import candidate_moves, search, winner, winning_cells


def main():
    board = [[0] * 13 for _ in range(13)]
    opening = [(6, 3), (6, 2), (6, 4), (3, 3), (6, 5), (4, 4), (6, 6)]
    human = iter([(10, 9), (10, 10), (9, 9)])
    moves = []
    for ply in range(14):
        player = 1 + ply % 2
        assert winner(board) == 0, "A legal replay must stop immediately at a terminal state"
        snapshot = [row[:] for row in board]
        if ply < len(opening):
            row, col = opening[ply]
            source, analysis = "scripted_opening", None
        elif player == 1:
            row, col = next(human)
            source, analysis = "scripted_black_move", None
        else:
            analysis = search(board, player, "alphabeta", 3, 8, None)
            assert analysis["completed_depth"] == 3 and not analysis["timeout"]
            row, col = analysis["move"]
            source = "actual_engine_search"
        assert board[row][col] == 0 and snapshot == board
        if ply == 7:
            assert candidate_moves(board, player, 8) == [(6, 7)], "The first recorded AI move must be a unique forced block"
        board[row][col] = player
        record = {"ply": ply + 1, "r": row, "c": col, "player": player, "source": source,
                  "board_before": snapshot, "winner_after": winner(board)}
        if analysis:
            record["analysis"] = analysis
        moves.append(record)
    assert winner(board) == 2
    data = {
        "schema_version": 1, "size": 13, "seed": 20261013,
        "randomness": "none: fixed scripted opening and deterministic engine",
        "description": "示例棋谱：前7手为预设合法布局；其后黑方为示例落子、白方为真实Alpha-Beta搜索。回放已加速，非棋力评测。",
        "rules": "freestyle-five-or-more", "algorithm": "alphabeta", "depth": 3,
        "max_candidates": 8, "time_limit_ms": None,
        "moves": moves, "winner": winner(board), "winning_cells": winning_cells(board),
        "runtime": {"python": sys.version, "platform": platform.platform()},
        "engine_sha256": hashlib.sha256((ROOT / "engine.py").read_bytes()).hexdigest(),
    }
    target = ROOT / "static/media/demo-game.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(moves)} legal plies; forced block at ply 8; white wins at ply 14: {target}")


if __name__ == "__main__":
    main()
