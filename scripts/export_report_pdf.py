"""Print the web report (static/report.html) to the downloadable PDF.

    python server.py --port 8801            # in another terminal
    python scripts/export_report_pdf.py --base http://127.0.0.1:8801
"""
import argparse
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "实验一五子棋实验报告.pdf"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


async def main(base: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROME)
        page = await browser.new_page(viewport={"width": 1100, "height": 1400})
        await page.goto(base + "/report.html", wait_until="networkidle")
        await page.evaluate("document.fonts.ready")
        await page.emulate_media(media="print")
        await page.wait_for_timeout(600)
        await page.pdf(path=str(OUT), format="A4", print_background=True, prefer_css_page_size=True)
        await browser.close()
    print("wrote", OUT, f"{OUT.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8801")
    asyncio.run(main(ap.parse_args().base.rstrip("/")))
