import sys, time, random
sys.path.insert(0, sys.argv[1])
from gomoku.engine import search, evaluate, winner

def selfplay_position(size, plies, seed):
    random.seed(seed)
    b = [[0]*size for _ in range(size)]
    m = size // 2
    b[m][m] = 1
    p = 2
    for i in range(plies - 1):
        r = search(b, p, depth=2, max_candidates=8, time_limit_ms=None)
        cands = [c["move"] for c in r["candidates"][:3]] or [r["move"]]
        mv = random.choice(cands) if i < 6 else r["move"]
        b[mv[0]][mv[1]] = p
        if winner(b): return None
        p = 3 - p
    return b, p

for seed in (3, 7):
    got = selfplay_position(15, 14, seed)
    if not got: print("seed", seed, "game ended"); continue
    b, p = got
    print("seed", seed, "stones", sum(v != 0 for row in b for v in row))
    for d in (2, 3, 4, 5):
        for algo in (("minimax", "alphabeta") if d <= 3 else ("alphabeta",)):
            t = time.perf_counter()
            r = search(b, p, algorithm=algo, depth=d, max_candidates=10, time_limit_ms=None)
            el = time.perf_counter() - t
            print(f"  {algo:9s} d={d}: {el:7.2f}s nodes={r['nodes']:7d} nps={r['nodes']/max(el,1e-9):6.0f} move={r['move']}")
            if el > 90: break
    r = search(b, p, depth=5, max_candidates=10, time_limit_ms=2000)
    print("  web default 2s budget -> completed depth", r["completed_depth"])
