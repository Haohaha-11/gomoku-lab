"""Record the gameplay demo video from the real game page.

    python -m gomoku.server --port 8801     # in another terminal
    python scripts/record_demo.py --base http://127.0.0.1:8801

Black is played by this script through the same /api/analyze engine (depth 4) and
entered with the keyboard, so the cursor moves visibly; white is the page's own AI
at its default settings (Alpha-Beta, depth 3). Frames come from Chrome's screencast
and are encoded with ffmpeg into web/media/gomoku-demo.mp4 plus a poster.
Recording pauses while the script itself is thinking, so there is no dead air.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.request

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "web" / "media"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
GPU_ARGS = ["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist"]
SIZE = 13


def parse_coord(text: str) -> tuple[int, int]:
    text = text.strip()
    return int(text[1:]) - 1, ord(text[0]) - 65


class Recorder:
    def __init__(self, cdp, folder: Path):
        self.cdp, self.folder, self.frames, self.on = cdp, folder, [], False
        cdp.on("Page.screencastFrame", self._frame)

    async def _frame(self, event):
        if self.on:
            path = self.folder / f"{len(self.frames):05d}.jpg"
            path.write_bytes(base64.b64decode(event["data"]))
            self.frames.append((path, event["metadata"]["timestamp"]))
        await self.cdp.send("Page.screencastFrameAck", {"sessionId": event["sessionId"]})

    async def start(self):
        self.on = True
        await self.cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92, "everyNthFrame": 1})

    async def pause(self):
        self.on = False
        await self.cdp.send("Page.stopScreencast")
        # the next frame continues straight from this one
        if self.frames:
            self.frames.append((self.frames[-1][0], None))


def engine_move(base: str, board, player: int, depth: int) -> tuple[int, int]:
    body = json.dumps({"board": board, "player": player, "algorithm": "alphabeta", "depth": depth,
                       "max_candidates": 10, "time_limit_ms": 2500}).encode()
    req = urllib.request.Request(base + "/api/analyze", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return tuple(json.load(response)["move"])


async def main(base: str, out: Path, black_depth: int):
    board = [[0] * SIZE for _ in range(SIZE)]
    cursor = [SIZE // 2, SIZE // 2]
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        async with async_playwright() as p:
            browser = await p.chromium.launch(executable_path=CHROME, args=GPU_ARGS)
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            cdp = await page.context.new_cdp_session(page)
            rec = Recorder(cdp, folder)
            await page.goto(base + "/game.html", wait_until="networkidle")
            await page.evaluate("document.fonts.ready")
            await page.wait_for_timeout(1200)
            await rec.start()
            await page.wait_for_timeout(1800)

            async def press_to(target):
                await page.focus("#board-hit")
                for axis, (up, down) in ((0, ("ArrowUp", "ArrowDown")), (1, ("ArrowLeft", "ArrowRight"))):
                    while cursor[axis] != target[axis]:
                        step = 1 if target[axis] > cursor[axis] else -1
                        await page.keyboard.press(down if step > 0 else up)
                        cursor[axis] += step
                        await page.wait_for_timeout(70)
                await page.wait_for_timeout(260)
                await page.keyboard.press("Enter")

            async def wait_turn():
                for _ in range(200):
                    label = await page.text_content("#turn-label")
                    if label in ("轮到你",) or "胜" in label or "和" in label:
                        return label
                    await page.wait_for_timeout(100)
                raise RuntimeError("AI did not answer in time")

            black_moves = 0
            result = ""
            while black_moves < 40:
                if black_moves == 0:
                    move = tuple(cursor)
                else:
                    await rec.pause()
                    move = engine_move(base, board, 1, black_depth)
                    await rec.start()
                await press_to(move)
                board[move[0]][move[1]] = 1
                black_moves += 1
                result = await wait_turn()
                if "胜" in result or "和" in result:
                    break
                white = parse_coord(await page.text_content("#candidates .candidate .coord"))
                board[white[0]][white[1]] = 2
                await page.wait_for_timeout(500)
                if black_moves == 5:  # show the hint and the candidate marks once
                    await page.click("#hint")
                    await page.mouse.move(720, 300)
                    await page.wait_for_selector(".toast.visible")
                    toast = await page.text_content("#toast")
                    cursor[:] = list(parse_coord(toast.split("建议落点")[1].split("·")[0]))
                    await page.wait_for_timeout(2200)
                if black_moves == 8:  # a look at the search statistics
                    await page.click("#analysis-drawer")
                    await page.mouse.move(720, 300)
                    await page.wait_for_timeout(2800)
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(500)
            await page.wait_for_timeout(4200)  # victory sweep
            await rec.pause()
            await browser.close()
        print(f"{result} after {black_moves} black moves, {len([f for f in rec.frames if f[1]])} frames")
        encode(rec.frames, folder, out)


def encode(frames, folder: Path, out: Path):
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    lines, last = [], None
    for i, (path, ts) in enumerate(frames):
        if ts is None:
            continue
        nxt = next((t for _, t in frames[i + 1:] if t is not None), None)
        gap = frames[i + 1][1] is None if i + 1 < len(frames) else False
        duration = 1 / 30 if (nxt is None or gap) else min(max(nxt - ts, 1 / 60), 0.5)
        lines.append(f"file '{path.as_posix()}'\nduration {duration:.4f}")
        last = path
    lines.append(f"file '{last.as_posix()}'")
    listing = folder / "frames.txt"
    listing.write_text("\n".join(lines), encoding="utf-8")
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
                    "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", "21",
                    "-movflags", "+faststart", str(out)], check=True)
    poster = out.with_name(out.stem + "-poster.jpg")
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-sseof", "-3.6", "-i", str(out), "-frames:v", "1",
                    "-q:v", "3", str(poster)], check=True)
    print("wrote", out, poster)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8801")
    ap.add_argument("--out", type=Path, default=MEDIA / "gomoku-demo.mp4")
    ap.add_argument("--black-depth", type=int, default=4)
    args = ap.parse_args()
    asyncio.run(main(args.base.rstrip("/"), args.out, args.black_depth))
