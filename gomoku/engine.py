"""Deterministic selective Gomoku search, with matched minimax / alpha-beta trees.

Rules are freestyle: black=1, white=2, and a line of at least five wins.
Candidate selection is deliberately local and capped; neither algorithm claims to
exhaustively solve the full legal-move tree. Only alpha-beta prunes score bounds.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import inf
from time import perf_counter
from typing import Callable

from third_party.husus_gomoku.patterns import create_pattern_dict  # MIT, see third_party/

WIN_SCORE = 100_000_000  # Dominates the nonterminal pattern table on supported boards.
TRACE_LIMIT = 320  # Keep browser payloads bounded without limiting the actual search.
DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))
Move = tuple[int, int]
PATTERNS = tuple(("".join({-1: "2", 0: "0", 1: "1"}[v] for v in pattern), score)
                 for pattern, score in create_pattern_dict().items())


def validate_board(board: list[list[int]]) -> int:
    """Validate geometry and stones; tactical puzzles need not have equal counts."""
    if not isinstance(board, list) or not 5 <= len(board) <= 19:
        raise ValueError("board must be a square list with size 5–19")
    size = len(board)
    for row in board:
        if not isinstance(row, list) or len(row) != size:
            raise ValueError("board must be square")
        if any(type(value) is not int or value not in (0, 1, 2) for value in row):
            raise ValueError("stones must be integers 0, 1, or 2")
    return size


def _line_at(board: list[list[int]], row: int, col: int, player: int) -> list[Move]:
    size = len(board)
    for dr, dc in DIRECTIONS:
        cells = [(row, col)]
        for sign in (-1, 1):
            r, c = row + sign * dr, col + sign * dc
            while 0 <= r < size and 0 <= c < size and board[r][c] == player:
                cells.append((r, c))
                r, c = r + sign * dr, c + sign * dc
        if len(cells) >= 5:
            return sorted(cells)
    return []


def winning_cells(board: list[list[int]]) -> list[list[int]]:
    validate_board(board)
    for r, row in enumerate(board):
        for c, player in enumerate(row):
            if player:
                line = _line_at(board, r, c, player)
                if line:
                    return [list(move) for move in line]
    return []


def winner(board: list[list[int]]) -> int:
    cells = winning_cells(board)
    return board[cells[0][0]][cells[0][1]] if cells else 0


@lru_cache(maxsize=15)
def _lines(size: int) -> tuple[tuple[Move, ...], ...]:
    lines = []
    for r in range(size):
        for c in range(size):
            for dr, dc in DIRECTIONS:
                if 0 <= r - dr < size and 0 <= c - dc < size:
                    continue
                line, rr, cc = [], r, c
                while 0 <= rr < size and 0 <= cc < size:
                    line.append((rr, cc))
                    rr, cc = rr + dr, cc + dc
                if len(line) >= 4:
                    lines.append(tuple(line))
    return tuple(lines)


def evaluate(board: list[list[int]], player: int) -> int:
    """Evaluate the MIT-licensed husus pattern table, including broken threats.

    Original scores are unchanged; the adapter scans maximal lines once, supports
    variable board sizes and maps upstream -1 to this API's white=2.
    """
    score = 0
    for cells in _lines(len(board)):
        line = "".join(str(board[r][c]) for r, c in cells)
        for pattern, value in PATTERNS:
            start = line.find(pattern)
            while start >= 0:
                score += value
                # Overlapping occurrences represent distinct threats on the board.
                start = line.find(pattern, start + 1)
    return score if player == 1 else -score


def _point_value(board: list[list[int]], r: int, c: int, player: int) -> tuple[bool, int]:
    size, value, winning = len(board), 0, False
    for dr, dc in DIRECTIONS:
        length, open_ends = 1, 0
        for sign in (-1, 1):
            rr, cc = r + sign * dr, c + sign * dc
            while 0 <= rr < size and 0 <= cc < size and board[rr][cc] == player:
                length += 1
                rr, cc = rr + sign * dr, cc + sign * dc
            open_ends += 0 <= rr < size and 0 <= cc < size and board[rr][cc] == 0
        if length >= 5:
            winning = True
            value += WIN_SCORE
        elif open_ends:
            # Four-in-a-row must rank above combinations of lower-order patterns.
            value += {1: (2, 4), 2: (80, 400), 3: (2_000, 20_000), 4: (100_000, 1_000_000)}[length][open_ends - 1]
    return winning, value


def candidate_moves(
    board: list[list[int]], player: int, max_candidates: int = 10,
    checkpoint: Callable[[], None] | None = None,
) -> list[Move]:
    """Search immediate wins or forced blocks first; otherwise cap radius-2 moves."""
    size = len(board)
    nearby: set[Move] = set()
    occupied = [(r, c) for r in range(size) for c in range(size) if board[r][c]]
    if not occupied:
        return [(size // 2, size // 2)]
    for r, c in occupied:
        for rr in range(max(0, r - 2), min(size, r + 3)):
            for cc in range(max(0, c - 2), min(size, c + 3)):
                if not board[rr][cc]:
                    nearby.add((rr, cc))
    ranked = []
    center = (size - 1) / 2
    for r, c in nearby:
        if checkpoint:
            checkpoint()
        wins, attack = _point_value(board, r, c, player)
        blocks, defense = _point_value(board, r, c, 3 - player)
        # The fixed 11:10 attack preference breaks equal-threat ties without changing the evaluator.
        rank = (-int(wins), -int(blocks), -(attack * 11 + defense * 10),
                (r - center) ** 2 + (c - center) ** 2, r, c)
        ranked.append((rank, (r, c), wins, blocks))
    # Coordinate tiebreaks make set iteration and PYTHONHASHSEED irrelevant.
    ranked.sort(key=lambda item: item[0])
    immediate_wins = [move for _, move, wins, _ in ranked if wins]
    if immediate_wins:
        return immediate_wins
    forced_blocks = [move for _, move, _, blocks in ranked if blocks]
    if forced_blocks:
        # Every nonblocking move loses next ply; retaining every block is cap-safe.
        return forced_blocks
    return [move for _, move, _, _ in ranked[:max_candidates]]


class _SearchTimeout(Exception):
    pass


@dataclass
class _Stats:
    nodes: int = 0
    leaves: int = 0
    cutoffs: int = 0
    pruned_branches: int = 0


def search(
    board: list[list[int]], player: int, algorithm: str = "alphabeta", depth: int = 3,
    max_candidates: int = 10, time_limit_ms: float | None = 2000,
) -> dict:
    """Search with iterative deepening and a cooperative wall-clock deadline.

    ``time_limit_ms=None`` or 0 disables the deadline for controlled benchmarks.
    Statistics include *all* attempted iterations; the returned decision, root
    scores and tree come from the last fully completed iteration. A deadline before
    depth one returns a legal deterministic fallback with completed_depth=0.
    """
    started = perf_counter()
    size = validate_board(board)
    if type(player) is not int or player not in (1, 2):
        raise ValueError("player must be 1 or 2")
    if algorithm not in ("minimax", "alphabeta"):
        raise ValueError("algorithm must be minimax or alphabeta")
    if type(depth) is not int or not 1 <= depth <= 6:
        raise ValueError("depth must be an integer from 1 to 6")
    if type(max_candidates) is not int or not 1 <= max_candidates <= 32:
        raise ValueError("max_candidates must be an integer from 1 to 32")
    if time_limit_ms is not None and (not isinstance(time_limit_ms, (float, int)) or not 0 <= time_limit_ms < inf):
        raise ValueError("time_limit_ms must be finite and nonnegative, or None")
    position = [row[:] for row in board]
    deadline = started + time_limit_ms / 1000 if time_limit_ms else inf
    stats = _Stats()
    terminal = winner(position)
    empty = [(r, c) for r in range(size) for c in range(size) if not position[r][c]]
    center = (size - 1) / 2
    fallback = min(empty, key=lambda m: ((m[0] - center) ** 2 + (m[1] - center) ** 2, m)) if empty else None
    result = {
        "move": list(fallback) if fallback and not terminal else None,
        "score": (WIN_SCORE if terminal == player else -WIN_SCORE) if terminal else 0,
        "algorithm": algorithm, "requested_depth": depth, "completed_depth": 0,
        "elapsed_ms": 0.0, "nodes": 0, "leaves": 0, "cutoffs": 0,
        "pruned_branches": 0, "timeout": False, "candidates": [], "pv": [],
        "tree": {"nodes": [], "truncated": False, "depth": 0, "limit": TRACE_LIMIT},
        "candidate_policy": "immediate wins, else forced blocks, else ordered radius-2 candidates with cap",
        "max_candidates": max_candidates, "stats_scope": "all iterative-deepening iterations",
        "score_kind": "terminal" if terminal or not empty else "fallback",
    }
    if terminal or not empty:
        result["nodes"] = result["leaves"] = 1
        result["elapsed_ms"] = round((perf_counter() - started) * 1000, 3)
        return result

    def checkpoint() -> None:
        if perf_counter() >= deadline:
            raise _SearchTimeout

    use_ab = algorithm == "alphabeta"
    for target_depth in range(1, depth + 1):
        trace: list[dict] = []
        trace_truncated = False

        def trace_add(parent: int | None, move: Move | None, ply: int, **extra) -> int | None:
            nonlocal trace_truncated
            if len(trace) >= TRACE_LIMIT:
                trace_truncated = True
                return None
            index = len(trace)
            trace.append({"id": index, "parent": parent, "move": list(move) if move else None,
                          "depth": ply, "score": None, **extra})
            return index

        def visit(remaining: int, turn: int, alpha: float, beta: float,
                  ply: int, last: Move | None, parent: int | None) -> tuple[int, list[Move]]:
            checkpoint()
            stats.nodes += 1
            node_id = trace_add(parent, last, ply)
            original_alpha, original_beta = alpha, beta
            if last is not None and _line_at(position, last[0], last[1], 3 - turn):
                stats.leaves += 1
                value = -WIN_SCORE + ply
                if node_id is not None:
                    trace[node_id].update(score=value, bound="exact", terminal=True)
                return value, []
            if ply == len(empty):
                stats.leaves += 1
                if node_id is not None:
                    trace[node_id].update(score=0, bound="exact", terminal=True)
                return 0, []
            if remaining == 0:
                stats.leaves += 1
                value = evaluate(position, turn)
                if node_id is not None:
                    trace[node_id].update(score=value, bound="exact")
                return value, []
            moves = candidate_moves(position, turn, max_candidates, checkpoint)
            if not moves:
                stats.leaves += 1
                if node_id is not None:
                    trace[node_id].update(score=0, bound="exact", terminal=True)
                return 0, []
            best, best_pv = -inf, []
            for index, move in enumerate(moves):
                r, c = move
                position[r][c] = turn
                try:
                    child_score, child_pv = visit(remaining - 1, 3 - turn,
                                                -beta if use_ab else -inf,
                                                -alpha if use_ab else inf,
                                                ply + 1, move, node_id)
                    score = -child_score
                finally:
                    # A timeout must restore every pending move before unwinding.
                    position[r][c] = 0
                if score > best:
                    best, best_pv = score, [move] + child_pv
                if use_ab:
                    alpha = max(alpha, best)
                    if alpha >= beta and index + 1 < len(moves):
                        skipped = len(moves) - index - 1
                        stats.cutoffs += 1
                        stats.pruned_branches += skipped
                        trace_add(node_id, moves[index + 1], ply + 1,
                                  pruned=True, pruned_count=skipped, bound="not_evaluated")
                        break
            bound = "exact"
            if use_ab and best <= original_alpha:
                bound = "upper_bound"
            elif use_ab and best >= original_beta:
                bound = "lower_bound"
            if node_id is not None:
                trace[node_id].update(score=int(best), bound=bound)
            return int(best), best_pv

        try:
            checkpoint()
            stats.nodes += 1
            root_id = trace_add(None, None, 0)
            moves = candidate_moves(position, player, max_candidates, checkpoint)
            best, best_move, best_pv, root_scores = -inf, moves[0], [], []
            alpha = -inf
            for move in moves:
                old_alpha = alpha
                r, c = move
                position[r][c] = player
                try:
                    child_score, child_pv = visit(target_depth - 1, 3 - player,
                                                -inf, -alpha if use_ab else inf,
                                                1, move, root_id)
                    score = -child_score
                finally:
                    position[r][c] = 0
                root_scores.append({"move": list(move), "score": score,
                                    "bound": "upper_bound" if use_ab and score <= old_alpha else "exact"})
                # Strict improvement preserves the same first-in-order tie winner.
                if score > best:
                    best, best_move, best_pv = score, move, [move] + child_pv
                alpha = max(alpha, best)
            checkpoint()
            trace[root_id].update(score=int(best), bound="exact")
            result.update(move=list(best_move), score=int(best), completed_depth=target_depth,
                          candidates=root_scores, pv=[list(m) for m in best_pv], score_kind="search",
                          tree={"nodes": trace, "truncated": trace_truncated,
                                "depth": target_depth, "limit": TRACE_LIMIT,
                                "score_perspective": "side to move at each node"})
        except _SearchTimeout:
            result["timeout"] = True
            break
    assert position == board, "search must restore its working board"
    result.update(vars(stats))
    result["elapsed_ms"] = round((perf_counter() - started) * 1000, 3)
    return result
