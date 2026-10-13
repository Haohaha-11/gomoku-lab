import sys, random, json, time
from multiprocessing import Pool
SNAP = sys.argv[1]
sys.path.insert(0, SNAP)
from gomoku.engine import search, winner
from vcf import vcf, five_points

BUDGET = 1000

def base_move(b, p):
    return search(b, p, depth=5, max_candidates=10, time_limit_ms=BUDGET)["move"]

def vcf_move(b, p):
    if not five_points(b, 3 - p):          # only attack when the opponent has no five-threat
        seq = vcf([row[:] for row in b], p, max_att=6)
        if seq: return list(seq[0])
    return base_move(b, p)

def play(args):
    seed, vcf_is_black = args
    random.seed(seed)
    b = [[0]*15 for _ in range(15)]
    b[7][7] = 1
    r, c = random.choice([(6, 6), (6, 7), (6, 8), (7, 8), (8, 8), (7, 6)]); b[r][c] = 2
    r, c = random.choice([m for m in ((5, 5), (5, 7), (8, 6), (6, 9), (9, 7), (8, 9)) if not b[m[0]][m[1]]]); b[r][c] = 1
    p = 2
    players = {1: vcf_move if vcf_is_black else base_move, 2: base_move if vcf_is_black else vcf_move}
    for ply in range(150):
        mv = players[p](b, p)
        if mv is None: return (seed, vcf_is_black, 0, ply)
        b[mv[0]][mv[1]] = p
        w = winner(b)
        if w: return (seed, vcf_is_black, w, ply)
        p = 3 - p
    return (seed, vcf_is_black, 0, 150)

if __name__ == "__main__":
    jobs = [(s, side) for s in range(8) for side in (True, False)]
    t = time.time()
    with Pool(8) as pool:
        res = pool.map(play, jobs)
    vcf_w = base_w = draw = 0
    for seed, vb, w, ply in res:
        if w == 0: draw += 1
        elif (w == 1) == vb: vcf_w += 1
        else: base_w += 1
    print(res)
    print(f"base+VCF wins {vcf_w}, base wins {base_w}, draws {draw} ({len(res)} games, {time.time()-t:.0f}s)")
