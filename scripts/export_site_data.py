"""Summarise results/benchmark.csv into static/data.js for the homepage and report charts."""
from collections import defaultdict
import csv
import json
from pathlib import Path
import statistics as st

ROOT = Path(__file__).resolve().parents[1]
# Baseline-engine probe (tools/probe): 2 s budget, VCF puzzle set and 16 test games.
PROBE = {"nps": [700, 900], "vcf_found": 1, "vcf_total": 10, "blunders": 53, "base_moves": 361,
         "losses_with_blunder": 8, "losses": 8}

rows = list(csv.DictReader(open(ROOT / "results" / "benchmark.csv", encoding="utf-8-sig")))
groups = defaultdict(list)
for r in rows:
    groups[(int(r["size"]), int(r["depth"]), r["algorithm"])].append(r)
bench = {}
for (size, depth, algo), rs in sorted(groups.items()):
    ms = [float(r["elapsed_ms"]) for r in rs]
    bench.setdefault(str(size), {}).setdefault(algo, []).append({
        "depth": depth, "nodes": round(st.mean(int(r["nodes"]) for r in rs), 1),
        "ms": round(st.mean(ms), 2), "sd": round(st.stdev(ms), 2), "n": len(rs)})
total = {a: sum(int(r["nodes"]) for r in rows if r["algorithm"] == a) for a in ("minimax", "alphabeta")}
data = {"bench": bench, "total_reduction": round(1 - total["alphabeta"] / total["minimax"], 4), "runs": len(rows), "probe": PROBE}
(ROOT / "static" / "data.js").write_text("window.GOMOKU_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")
print("wrote static/data.js from", len(rows), "rows")
