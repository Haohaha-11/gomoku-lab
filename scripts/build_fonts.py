"""Subset the self-hosted OFL fonts to the characters the pages actually use.

    python scripts/build_fonts.py

Source fonts are downloaded once into scripts/.fonts-src (git-ignored). Re-run after
changing any brush-font text in web/*.html or the HUD strings in web/js/game.js.
"""
from pathlib import Path
import re
import urllib.request
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parents[1]
STATIC, SRC, OUT = ROOT / "web", ROOT / "scripts" / ".fonts-src", ROOT / "web" / "fonts"
GOOGLE = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
SOURCES = {
    "MaShanZheng-Regular.ttf": GOOGLE + "mashanzheng/MaShanZheng-Regular.ttf",
    "NotoSerifSC[wght].ttf": GOOGLE + "notoserifsc/NotoSerifSC%5Bwght%5D.ttf",
    "OFL.txt": GOOGLE + "mashanzheng/OFL.txt",
}
ASCII = "".join(chr(c) for c in range(0x20, 0x7F))
PUNCT = "·，。、：；！？「」（）《》—…“”‘’×→←↗↓"

pages = "".join(p.read_text(encoding="utf-8") for p in sorted(STATIC.glob("*.html")))
app = (STATIC / "js" / "game.js").read_text(encoding="utf-8")
brush_classes = r'class="(?:eyebrow|name|panel-title|turn-label)"[^>]*>([^<]+)<'
brush = ("身入弈坐忘境，。五子棋实验报告目录一二三四五六七八九十〇剪掉个叶子黑白胜和轮到你对手思考中等待"
         + "".join(re.findall(brush_classes, pages))
         + "".join(re.findall(r"<h1>(.*?)</h1>|<h2>([^<]*)</h2>", pages) and
                   [x for pair in re.findall(r"<h1>(.*?)</h1>|<h2>([^<]*)</h2>", pages) for x in pair])
         + "".join(re.findall(r"turn-label'\)\.textContent=([^;]+);", app))
         + "0123456789.,/k")
serif = "".join(re.findall(r'class="sub"[^>]*>(.*?)</p>', pages)) + "".join(re.findall(r'class="engine[^"]*"><strong>([^<]+)<', pages)) + ASCII + PUNCT


def source(name: str) -> Path:
    path = SRC / name
    if not path.exists():
        SRC.mkdir(parents=True, exist_ok=True)
        print("downloading", name)
        urllib.request.urlretrieve(SOURCES[name], path)
    return path


def build(src: Path, text: str, out: str, wght: float | None = None):
    font = TTFont(src)
    if wght is not None and "fvar" in font:
        font = instancer.instantiateVariableFont(font, {"wght": wght})
    opts = subset.Options()
    opts.flavor, opts.layout_features, opts.name_IDs, opts.hinting = "woff2", ["*"], ["*"], False
    sub = subset.Subsetter(opts)
    sub.populate(text="".join(sorted(set(text))))
    sub.subset(font)
    font.flavor = "woff2"
    font.save(OUT / out)
    print(f"{out}: {len(set(text))} chars, {(OUT / out).stat().st_size / 1024:.1f} KB")


OUT.mkdir(exist_ok=True)
build(source("MaShanZheng-Regular.ttf"), brush, "brush.woff2")
build(source("NotoSerifSC[wght].ttf"), serif, "serif.woff2", wght=500)
(OUT / "OFL.txt").write_text(source("OFL.txt").read_text(encoding="utf-8"), encoding="utf-8")
