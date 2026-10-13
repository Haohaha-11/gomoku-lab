"""Offline export for manual review; the public website never exposes feedback."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/feedback.sqlite3"))
    parser.add_argument("--output", type=Path, default=Path("results/feedback.jsonl"))
    args = parser.parse_args()
    if not args.db.is_file():
        parser.error("Feedback database does not exist")
    with closing(sqlite3.connect(f"file:{args.db.resolve().as_posix()}?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM feedback ORDER BY id").fetchall()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as output:
        for row in rows:
            record = dict(row)
            for key in ("board", "ai_move", "preferred_move"):
                record[key] = json.loads(record[key]) if record[key] else None
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Exported {len(rows)} unverified feedback records to {args.output}")


if __name__ == "__main__":
    main()
