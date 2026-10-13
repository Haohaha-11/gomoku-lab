import sys, random, time
from multiprocessing import Pool
sys.path.insert(0, sys.argv[1])
from engine import search, winner
from vcf import vcf, five_points
import probe_match as pm

STATS = {"blunders": 0, "moves": 0}

def base_move_logged(b, p):
    mv = pm.base_move(b, p)
    return mv

def guarded_move(b, p):
    """VCF attack + refuse root moves that hand the opponent a VCF."""
    if not five_points(b, 3 - p):
        seq = vcf([row[:] for row in b], p, max_att=6)
        if seq: return list(seq[0])
    res = search(b, p, depth=5, max_candidates=10, time_limit_ms=pm.BUDGET)
    order = [c["move"] for c in sorted(res["candidates"], key=lambda c: -c["score"])] or [res["move"]]
    for mv in order:
        bb = [row[:] for row in b]; bb[mv[0]][mv[1]] = p
        if five_points(bb, p): return mv
        if not vcf(bb, 3 - p, max_att=5): return mv
    return res["move"]

def play(args):
    seed, g_black = args
    random.seed(seed)
    b = [[0]*15 for _ in range(15)]
    b[7][7] = 1
    r, c = random.choice([(6, 6), (6, 7), (6, 8), (7, 8), (8, 8), (7, 6)]); b[r][c] = 2
    r, c = random.choice([m for m in ((5, 5), (5, 7), (8, 6), (6, 9), (9, 7), (8, 9)) if not b[m[0]][m[1]]]); b[r][c] = 1
    p = 2
    players = {1: guarded_move if g_black else pm.base_move, 2: pm.base_move if g_black else guarded_move}
    blunders = 0; base_moves = 0
    for ply in range(150):
        mover_is_base = players[p] is pm.base_move
        mv = players[p](b, p)
        b[mv[0]][mv[1]] = p
        w = winner(b)
        if w: return (seed, g_black, w, ply, blunders, base_moves)
        if mover_is_base:
            base_moves += 1
            if not five_points(b, p) and vcf([row[:] for row in b], 3 - p, max_att=5): blunders += 1
        p = 3 - p
    return (seed, g_black, 0, 150, blunders, base_moves)

if __name__ == "__main__":
    jobs = [(s, side) for s in range(8) for side in (True, False)]
    t = time.time()
    with Pool(8) as pool:
        res = pool.map(play, jobs)
    gw = bw = d = 0; bl = bm = 0; lost_with_blunder = 0
    for seed, gb, w, ply, blunders, base_moves in res:
        bl += blunders; bm += base_moves
        if w == 0: d += 1
        elif (w == 1) == gb:
            gw += 1; lost_with_blunder += blunders > 0
        else: bw += 1
    print(res)
    print(f"guarded(VCF attack+defence) wins {gw}, base wins {bw}, draws {d}; {time.time()-t:.0f}s")
    print(f"base moves that handed the opponent a VCF: {bl}/{bm}; base losses containing such a blunder: {lost_with_blunder}/{gw}")
