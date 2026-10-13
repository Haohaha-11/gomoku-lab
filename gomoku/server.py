"""Gomoku demo server: static site from web/ plus the search and feedback API.

Run from the repository root:  python -m gomoku.server --port 8767
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
from contextlib import closing
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
from urllib.parse import unquote, urlsplit

from gomoku.engine import search, winner

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("GOMOKU_DATA_DIR", str(ROOT / "data")))
SEARCH_SLOTS = threading.BoundedSemaphore(2)
RATE_LOCK = threading.Lock()
RATE_BUCKETS: dict[str, deque] = defaultdict(deque)
MAX_BODY = 32768
# The GitHub Pages copy of the site calls this API from another origin.
ALLOWED_ORIGINS = frozenset(o.strip() for o in os.environ.get(
    "GOMOKU_ALLOWED_ORIGINS", "https://haohaha-11.github.io").split(",") if o.strip())


def initialize_database():
    DATA.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DATA / "feedback.sqlite3")) as db, db:
        db.execute("""CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY, created_at TEXT NOT NULL,
            board TEXT NOT NULL, player INTEGER NOT NULL,
            ai_move TEXT NOT NULL, rating INTEGER NOT NULL,
            preferred_move TEXT, comment TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'unverified_human_feedback')""")


def integer(value, name, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer between {low} and {high}")
    return value


def game_input(payload):
    board = payload.get("board")
    if not isinstance(board, list) or len(board) not in (9, 13, 15):
        raise ValueError("board must be 9, 13 or 15 square")
    n = len(board)
    if any(not isinstance(row, list) or len(row) != n for row in board):
        raise ValueError("board must be square")
    if any(type(cell) is not int or cell not in (0, 1, 2) for row in board for cell in row):
        raise ValueError("board cells must be integers 0, 1 or 2")
    black = sum(row.count(1) for row in board)
    white = sum(row.count(2) for row in board)
    player = integer(payload.get("player"), "player", 1, 2)
    if black not in (white, white + 1):
        raise ValueError("invalid stone counts: black moves first")
    if player != (1 if black == white else 2):
        raise ValueError("player does not match the side to move")
    return board, player


def coordinate(value, board, name):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{name} must be [row,column]")
    r, c = [integer(v, name, 0, len(board) - 1) for v in value]
    if board[r][c]:
        raise ValueError(f"{name} must point to an empty intersection")
    return [r, c]


class Handler(BaseHTTPRequestHandler):
    server_version = "GomokuLab/1.0"

    def setup(self):
        super().setup()
        self.connection.settimeout(12)

    def log_message(self, fmt, *args):
        # Do not put submitted feedback or request bodies in logs.
        print(f"{self.log_date_time_string()} {fmt % args}", flush=True)

    def cors_origin(self):
        origin = self.headers.get("Origin")
        return origin if origin in ALLOWED_ORIGINS else None

    def response_headers(self, content_type, length, download=None):
        if self.cors_origin():
            self.send_header("Access-Control-Allow-Origin", self.cors_origin())
            self.send_header("Vary", "Origin")
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'")
        if download:
            self.send_header("Content-Disposition", f'attachment; filename="{download}"')

    def send_bytes(self, status, body, content_type, download=None):
        self.send_response(status)
        self.response_headers(content_type, len(body), download)
        self.end_headers()
        if self.command != "HEAD":
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def send_file(self, target, content_type, download=None):
        # Browser video seeking requests byte ranges. Stream only that segment so
        # several viewers do not load whole recordings into server memory.
        size = target.stat().st_size
        start, end = 0, size - 1
        requested = self.headers.get("Range") if self.command == "GET" else None
        if requested:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", requested.strip())
            try:
                if not match or not any(match.groups()) or not size:
                    raise ValueError
                left, right = match.groups()
                if left:
                    start = int(left)
                    end = min(int(right), size - 1) if right else size - 1
                else:
                    length = int(right)
                    if length <= 0:
                        raise ValueError
                    start = max(0, size - length)
                if start >= size or end < start:
                    raise ValueError
            except ValueError:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.response_headers(content_type, 0)
                self.end_headers()
                return
        self.send_response(206 if requested else 200)
        self.send_header("Accept-Ranges", "bytes")
        if requested:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.response_headers(content_type, max(0, end - start + 1), download)
        self.end_headers()
        if self.command == "HEAD":
            return
        try:
            with target.open("rb") as source:
                source.seek(start)
                remaining = end - start + 1
                while remaining > 0:
                    chunk = source.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def json(self, status, value):
        self.send_bytes(status, json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_HEAD(self):
        self.do_GET()

    def do_OPTIONS(self):
        # CORS preflight for JSON posts from an allowed origin.
        if not self.cors_origin() or not urlsplit(self.path).path.startswith("/api/"):
            self.json(403, {"error": "Cross-origin requests are not allowed"})
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", self.cors_origin())
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Vary", "Origin")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        if path == "/api/health":
            self.json(200, {"status": "ok", "engine": "python", "version": "1.0", "rules": "freestyle-five-or-more", "learning": "feedback-collection-only"})
            return
        if path == "/api/benchmarks":
            summary = ROOT / "experiments" / "results" / "summary.json"
            if summary.exists():
                self.send_bytes(200, summary.read_bytes(), "application/json; charset=utf-8")
            else:
                self.json(503, {"error": "Benchmarks are not available yet"})
            return
        downloads = {
            "/downloads/report.pdf": (ROOT / "docs" / "实验一五子棋实验报告.pdf", "gomoku-report.pdf"),
            "/downloads/benchmark.csv": (ROOT / "experiments" / "results" / "benchmark.csv", "gomoku-benchmark.csv"),
        }
        if path in downloads:
            target, filename = downloads[path]
            if target.is_file():
                self.send_file(target, mimetypes.guess_type(filename)[0] or "application/octet-stream",
                                None if filename.endswith(".html") else filename)
            else:
                self.json(404, {"error": "Download is not available"})
            return
        static = (ROOT / "web").resolve()
        target = (static / (path.lstrip("/") or "index.html")).resolve()
        if not target.is_relative_to(static) or not target.is_file():
            self.json(404, {"error": "Not found"})
            return
        mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if target.suffix in (".js", ".mjs"):
            mime = "text/javascript"
        if mime.startswith("text/"):
            mime += "; charset=utf-8"
        self.send_file(target, mime)

    def permitted_request(self):
        origin = self.headers.get("Origin")
        if origin and urlsplit(origin).netloc != self.headers.get("Host") and origin not in ALLOWED_ORIGINS:
            self.json(403, {"error": "Cross-origin submissions are not allowed"})
            return False
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip() != "application/json":
            self.json(415, {"error": "Send application/json"})
            return False
        peer = self.client_address[0]
        if peer in ("127.0.0.1", "::1"):
            peer = self.headers.get("X-Forwarded-For", peer).split(",")[-1].strip()
        now = time.monotonic()
        with RATE_LOCK:
            bucket = RATE_BUCKETS[peer]
            while bucket and now - bucket[0] > 60:
                bucket.popleft()
            if len(bucket) >= 90:
                self.json(429, {"error": "Please wait before submitting more requests"})
                return False
            bucket.append(now)
            # Expire idle clients so a public classroom demo has bounded bookkeeping.
            if len(RATE_BUCKETS) > 1024:
                for key in list(RATE_BUCKETS):
                    if not RATE_BUCKETS[key] or now - RATE_BUCKETS[key][-1] > 60:
                        del RATE_BUCKETS[key]
        return True

    def do_POST(self):
        if not self.permitted_request():
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY:
                self.json(413, {"error": "Request body must be between 1 and 32768 bytes"})
                return
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("JSON object required")
            path = urlsplit(self.path).path
            if path == "/api/analyze":
                board, player = game_input(payload)
                algorithm = payload.get("algorithm", "alphabeta")
                if algorithm not in ("minimax", "alphabeta"):
                    raise ValueError("algorithm must be minimax or alphabeta")
                depth = integer(payload.get("depth", 3), "depth", 1, 5)
                cap = integer(payload.get("max_candidates", 10), "max_candidates", 4, 12)
                budget = integer(payload.get("time_limit_ms", 2000), "time_limit_ms", 100, 4000)
                if not SEARCH_SLOTS.acquire(blocking=False):
                    self.json(429, {"error": "AI is busy. Please try again shortly."})
                    return
                try:
                    result = search(board, player, algorithm=algorithm, depth=depth, max_candidates=cap, time_limit_ms=budget)
                finally:
                    SEARCH_SLOTS.release()
                self.json(200, result)
            elif path == "/api/feedback":
                board, player = game_input(payload)
                if winner(board):
                    raise ValueError("Feedback must contain the position before the AI move")
                ai_move = coordinate(payload.get("ai_move"), board, "ai_move")
                rating = integer(payload.get("rating"), "rating", -1, 1)
                if rating == 0:
                    raise ValueError("rating must be -1 or 1")
                preferred = payload.get("preferred_move")
                if preferred is not None:
                    preferred = coordinate(preferred, board, "preferred_move")
                comment = payload.get("comment", "")
                if not isinstance(comment, str) or len(comment) > 500:
                    raise ValueError("comment must be at most 500 characters")
                with closing(sqlite3.connect(DATA / "feedback.sqlite3", timeout=5)) as db, db:
                    cursor = db.execute("INSERT INTO feedback(created_at,board,player,ai_move,rating,preferred_move,comment) VALUES(?,?,?,?,?,?,?)", (
                        datetime.now(timezone.utc).isoformat(), json.dumps(board), player,
                        json.dumps(ai_move), rating, json.dumps(preferred) if preferred else None, comment))
                self.json(201, {"status": "saved", "id": cursor.lastrowid, "training_applied": False})
            else:
                self.json(404, {"error": "Not found"})
        except (ValueError, TypeError, KeyError, UnicodeDecodeError) as exc:
            self.json(400, {"error": str(exc)})
        except Exception:
            self.log_error("request failed")
            self.json(500, {"error": "Server error; please retry"})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args()
    initialize_database()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Gomoku Lab serving http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
