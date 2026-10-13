"""Reproducible matched-tree comparison; writes raw measurements and provenance."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import random
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gomoku.engine import search, winner

SEED = 20261013
SIZES = (9, 13, 15)
DEPTHS = (1, 2, 3)
CAP = 8


def make_positions(seed: int = SEED) -> list[dict]:
    rng = random.Random(seed)
    offsets = [(r, c) for r in range(-2, 3) for c in range(-2, 3)]
    patterns = []
    for sample in range(3):
        # The same legal 8-ply opening is centered on all sizes to control position difficulty.
        while True:
            chosen = rng.sample(offsets, 8)
            probe = [[0] * 9 for _ in range(9)]
            legal = True
            for ply, (dr, dc) in enumerate(chosen):
                probe[4 + dr][4 + dc] = 1 + ply % 2
                if winner(probe):
                    legal = False
                    break
            if legal:
                break
        patterns.append(chosen)
    positions = []
    for size in SIZES:
        for index, chosen in enumerate(patterns):
            board = [[0] * size for _ in range(size)]
            moves = []
            for ply, (dr, dc) in enumerate(chosen):
                r, c = size // 2 + dr, size // 2 + dc
                board[r][c] = 1 + ply % 2
                moves.append([r, c])
            assert winner(board) == 0
            assert sum(row.count(1) for row in board) == sum(row.count(2) for row in board)
            positions.append({"id": f"s{size}-p{index}", "size": size, "sample": index,
                              "player": 1, "board": board, "moves": moves})
    return positions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path, default=ROOT / "experiments" / "results")
    args = parser.parse_args()
    if not 1 <= args.repeats <= 20:
        parser.error("--repeats must be 1–20")
    args.output.mkdir(parents=True, exist_ok=True)
    positions = make_positions()
    # Warm both implementations and populate the shared geometry cache before timing.
    for position in positions[::3]:
        for algorithm in ("minimax", "alphabeta"):
            search(position["board"], 1, algorithm, 1, CAP, None)
    rows, checks = [], []
    for position in positions:
        for depth in DEPTHS:
            for repeat in range(args.repeats):
                pair = {}
                # Alternate execution order to reduce systematic warm-cache/thermal bias.
                algorithms = ("minimax", "alphabeta") if repeat % 2 == 0 else ("alphabeta", "minimax")
                for algorithm in algorithms:
                    result = search(position["board"], 1, algorithm, depth, CAP, None)
                    assert result["completed_depth"] == depth and not result["timeout"]
                    pair[algorithm] = result
                    rows.append({"position": position["id"], "size": position["size"],
                                 "sample": position["sample"], "seed": SEED, "depth": depth,
                                 "repeat": repeat + 1, "algorithm": algorithm, "cap": CAP,
                                 "score": result["score"], "move_row": result["move"][0],
                                 "move_col": result["move"][1],
                                 **{name: result[name] for name in ("elapsed_ms", "nodes", "leaves", "cutoffs", "pruned_branches", "completed_depth", "timeout")}})
                mm, ab = pair["minimax"], pair["alphabeta"]
                equal = (mm["move"], mm["score"]) == (ab["move"], ab["score"])
                assert equal, f"search mismatch for {position['id']}, depth {depth}"
                assert ab["nodes"] <= mm["nodes"]
                checks.append({"position": position["id"], "depth": depth, "repeat": repeat + 1,
                               "score_and_move_equal": equal,
                               "node_reduction_pct": round(100 * (1 - ab["nodes"] / mm["nodes"]), 3)})
            print(f"completed {position['id']} depth={depth}", flush=True)
    aggregates = []
    for size in SIZES:
        for depth in DEPTHS:
            pair = {}
            for algorithm in ("minimax", "alphabeta"):
                selected = [r for r in rows if r["size"] == size and r["depth"] == depth and r["algorithm"] == algorithm]
                group = {"size": size, "depth": depth, "algorithm": algorithm,
                         "n_positions": 3, "n_measurements": len(selected),
                         "mean_ms": round(statistics.mean(r["elapsed_ms"] for r in selected), 3),
                         "median_ms": round(statistics.median(r["elapsed_ms"] for r in selected), 3),
                         "std_ms": round(statistics.stdev(r["elapsed_ms"] for r in selected), 3),
                         "mean_nodes": round(statistics.mean(r["nodes"] for r in selected), 3),
                         "mean_leaves": round(statistics.mean(r["leaves"] for r in selected), 3),
                         "mean_cutoffs": round(statistics.mean(r["cutoffs"] for r in selected), 3)}
                pair[algorithm] = group
                aggregates.append(group)
            ab = pair["alphabeta"]
            ab["node_reduction_pct"] = round(100 * (1 - ab["mean_nodes"] / pair["minimax"]["mean_nodes"]), 3)
            ab["speedup_vs_minimax"] = round(pair["minimax"]["mean_ms"] / ab["mean_ms"], 3)
    source_files = [ROOT / "gomoku" / "engine.py", Path(__file__), ROOT / "third_party/husus_gomoku/patterns.py"]
    summary = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {"python": sys.version, "platform": platform.platform(),
                        "machine": platform.machine(), "processor": platform.processor(),
                        "logical_cpus": os.cpu_count()},
        "config": {"seed": SEED, "sizes": list(SIZES), "depths": list(DEPTHS), "positions_per_size": 3,
                   "plies_per_position": 8, "repeats": args.repeats, "max_candidates": CAP,
                   "time_limit_ms": None, "algorithms": ["minimax", "alphabeta"]},
        "fairness": ["Same positions, evaluator, tactical reduction, candidate cap and deterministic ordering.",
                     "Timing and node counts include all iterative-deepening iterations.",
                     "No timeout; every measured call completes its requested depth.",
                     "Order alternates by repeat; each board-size geometry cache warmed before measurement.",
                     "Score and selected move asserted equal on every paired call.",
                     "Board size reuses identical centered opening offsets; it primarily changes edge effects and evaluation cost under local candidate selection."],
        "limitations": ["Selective radius-2 search with cap=8 is not exhaustive whole-board minimax.",
                        "Immediate wins are searched exclusively; otherwise immediate opponent wins force blocking candidates, which may exceed the cap.",
                        "Only three synthetic legal opening positions; this measures computation, not playing strength or win rate.",
                        "Wall times vary with hardware and concurrent load; node counts are deterministic."],
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files},
        "positions": positions, "rows": rows, "aggregates": aggregates,
        "equivalence": {"paired_checks": len(checks), "passed": sum(c["score_and_move_equal"] for c in checks),
                        "unique_position_depth_pairs": len(positions) * len(DEPTHS), "checks": checks},
    }
    with (args.output / "benchmark.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (args.output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"measurements": len(rows), "paired_checks": len(checks), "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
