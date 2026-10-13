"""Minimal VCF (victory by continuous fours) solver used to probe the GPT engine."""
DIRS = ((0, 1), (1, 0), (1, 1), (1, -1))

def makes_five(b, r, c, p):
    n = len(b)
    for dr, dc in DIRS:
        k = 1
        for s in (1, -1):
            rr, cc = r + s*dr, c + s*dc
            while 0 <= rr < n and 0 <= cc < n and b[rr][cc] == p:
                k += 1; rr += s*dr; cc += s*dc
        if k >= 5: return True
    return False

def near_empty(b, radius=2):
    n = len(b); out = set()
    for r in range(n):
        for c in range(n):
            if b[r][c]:
                for rr in range(max(0, r-radius), min(n, r+radius+1)):
                    for cc in range(max(0, c-radius), min(n, c+radius+1)):
                        if not b[rr][cc]: out.add((rr, cc))
    return out

def five_points(b, p, cells=None):
    cells = near_empty(b, 4) if cells is None else cells
    return [m for m in cells if not b[m[0]][m[1]] and makes_five(b, m[0], m[1], p)]

def vcf(b, p, max_att=10):
    """Return the attacker's winning sequence (attacker+defender moves) or None."""
    if max_att == 0: return None
    if five_points(b, p): return [five_points(b, p)[0]]
    if five_points(b, 3-p): return None  # defender threatens five; not handled (strict VCF)
    for m in sorted(near_empty(b, 2)):
        r, c = m
        b[r][c] = p
        threats = five_points(b, p)
        if threats:
            if len(threats) >= 2:  # open four / double four: defender can't block both
                b[r][c] = 0
                return [m, threats[0], "*", threats[1]]
            br, bc = threats[0]
            b[br][bc] = 3 - p
            sub = vcf(b, p, max_att - 1)
            b[br][bc] = 0
            if sub is not None:
                b[r][c] = 0
                return [m, (br, bc)] + sub
        b[r][c] = 0
    return None
