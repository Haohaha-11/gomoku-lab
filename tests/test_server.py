"""Exercise HTTP boundaries and persisted feedback without touching demo data."""
import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from gomoku import server


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.previous = server.DATA
        server.DATA = Path(cls.temp.name)
        server.initialize_database()
        cls.http = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.http.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join()
        server.DATA = cls.previous
        cls.temp.cleanup()

    def request(self, path, data=None, headers=None):
        headers = headers or {}
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = Request(self.base + path, data=json.dumps(data).encode() if data is not None else None, headers=headers)
        try:
            response = urlopen(req, timeout=10)
        except HTTPError as exc:
            response = exc
        with response:
            return response.status, json.loads(response.read())

    def position(self):
        board = [[0] * 9 for _ in range(9)]
        board[4][4] = 1
        return {"board": board, "player": 2, "depth": 1}

    def test_live_search(self):
        code, result = self.request("/api/analyze", self.position())
        self.assertEqual(code, 200)
        self.assertEqual(result["completed_depth"], 1)
        r, c = result["move"]
        self.assertEqual(self.position()["board"][r][c], 0)
        self.assertGreater(result["nodes"], 0)

    def test_invalid_input_and_depth(self):
        payload = self.position()
        payload["player"] = 1
        self.assertEqual(self.request("/api/analyze", payload)[0], 400)
        payload = self.position()
        payload["depth"] = 100
        self.assertEqual(self.request("/api/analyze", payload)[0], 400)
        payload = self.position()
        payload["board"][0][0] = True
        self.assertEqual(self.request("/api/analyze", payload)[0], 400)

    def test_origin_and_traversal(self):
        self.assertEqual(self.request("/api/analyze", self.position(), {"Origin": "https://unrelated.example"})[0], 403)
        self.assertEqual(self.request("/%2e%2e/server.py")[0], 404)

    def test_allowed_origin_cors(self):
        origin = "https://haohaha-11.github.io"
        status, _ = self.request("/api/analyze", self.position(), {"Origin": origin})
        self.assertEqual(status, 200)
        with urlopen(Request(self.base + "/api/analyze", method="OPTIONS",
                             headers={"Origin": origin, "Access-Control-Request-Method": "POST"})) as response:
            self.assertEqual(response.status, 204)
            self.assertEqual(response.headers["Access-Control-Allow-Origin"], origin)
        with urlopen(Request(self.base + "/api/health", headers={"Origin": origin})) as response:
            self.assertEqual(response.headers["Access-Control-Allow-Origin"], origin)
        with self.assertRaises(HTTPError) as error:
            urlopen(Request(self.base + "/api/analyze", method="OPTIONS", headers={"Origin": "https://unrelated.example"}))
        self.assertEqual(error.exception.code, 403)

    def test_video_ranges_and_head(self):
        previous_root = server.ROOT
        fixture = Path(self.temp.name) / "web"
        fixture.mkdir(exist_ok=True)
        (fixture / "clip.mp4").write_bytes(b"0123456789")
        server.ROOT = Path(self.temp.name)
        try:
            for spec, body, interval in (("bytes=2-5", b"2345", "2-5"),
                                         ("bytes=8-", b"89", "8-9"),
                                         ("bytes=-3", b"789", "7-9")):
                with urlopen(Request(self.base + "/clip.mp4", headers={"Range": spec})) as response:
                    self.assertEqual(response.status, 206)
                    self.assertEqual(response.headers["Content-Range"], f"bytes {interval}/10")
                    self.assertEqual(response.read(), body)
            with urlopen(Request(self.base + "/clip.mp4", method="HEAD")) as response:
                self.assertEqual(response.headers["Content-Length"], "10")
                self.assertEqual(response.read(), b"")
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(self.base + "/clip.mp4", headers={"Range": "bytes=12-"}))
            self.assertEqual(error.exception.code, 416)
            self.assertEqual(error.exception.headers["Content-Range"], "bytes */10")
            error.exception.close()
        finally:
            server.ROOT = previous_root

    def test_feedback_is_persisted_and_does_not_train(self):
        payload = self.position() | {"ai_move": [4, 5], "rating": -1, "preferred_move": [5, 4], "comment": "Prefer central defense"}
        code, result = self.request("/api/feedback", payload)
        self.assertEqual(code, 201)
        self.assertFalse(result["training_applied"])
        with closing(sqlite3.connect(server.DATA / "feedback.sqlite3")) as db:
            stored = db.execute("SELECT player,rating,preferred_move,comment,source FROM feedback WHERE id=?", (result["id"],)).fetchone()
        self.assertEqual(stored[:3], (2, -1, "[5, 4]"))
        self.assertEqual(stored[4], "unverified_human_feedback")

    def test_feedback_rejects_occupied_move(self):
        payload = self.position() | {"ai_move": [4, 4], "rating": 1}
        self.assertEqual(self.request("/api/feedback", payload)[0], 400)


if __name__ == "__main__":
    unittest.main()
