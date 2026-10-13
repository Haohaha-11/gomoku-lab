import sys, time, random, json
sys.path.insert(0, sys.argv[1])
from engine import search, winner
from vcf import vcf, five_points

def empty(n): return [[0]*n for _ in range(n)]

# T1: white has an open three on row 7; black has quiet stones. Black must block (or make a four).
b = empty(15)
for c in (5, 6, 7): b[7][c] = 2
for m in ((5, 9), (9, 4), (10, 10)): b[m[0]][m[1]] = 1
b[3][3] = 2  # balance counts: black 3, white 4 -> make black to move with 4/4
b[11][2] = 1
r = search(b, 1, depth=3, time_limit_ms=2000)
print("T1 block open three -> AI plays", r["move"], "(correct: one of [7,4] [7,8] or a four)")

# Collect VCF puzzles from randomized self-play with the GPT engine itself.
random.seed(11)
puzzles = []
for g in range(60):
    if len(puzzles) >= 12: break
    b = empty(15); b[7][7] = 1; p = 2
    for ply in range(40):
        res = search(b, p, depth=2, max_candidates=8, time_limit_ms=None)
        cands = [c["move"] for c in res["candidates"][:4]] or [res["move"]]
        mv = random.choice(cands) if ply < 10 else res["move"]
        b[mv[0]][mv[1]] = p
        if winner(b): break
        p = 3 - p
        if ply >= 8 and not five_points(b, p) and not five_points(b, 3-p):
            seq = vcf([row[:] for row in b], p, max_att=8)
            if seq and len([x for x in seq if x != "*"]) >= 7:
                puzzles.append(([row[:] for row in b], p, seq)); break
print("found", len(puzzles), "VCF puzzles with >=7-ply forced wins")
solved = 0
for i, (b, p, seq) in enumerate(puzzles):
    r = search(b, p, depth=5, max_candidates=10, time_limit_ms=2000)
    first = list(seq[0])
    plies = len([x for x in seq if x != "*"])
    # does the engine's move still keep a forced win (any VCF), not just the same first move?
    bb = [row[:] for row in b]; bb[r["move"][0]][r["move"][1]] = p
    ok = r["score"] >= 10**7 or r["move"] == first
    solved += ok
    print(f"P{i}: VCF {plies} plies, first={first}; engine(2s) -> {r['move']} depth {r['completed_depth']} score {r['score']} {'OK' if ok else 'MISSED'}")
print("engine found forced win in", solved, "/", len(puzzles))
json.dump([(b, p, [list(x) if x != '*' else x for x in s]) for b, p, s in puzzles], open("vcf_puzzles.json", "w"))
