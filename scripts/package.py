"""Build a reproducible source ZIP and deployment tar, excluding runtime feedback."""
from pathlib import Path
import tarfile
import zipfile

root = Path(__file__).resolve().parents[1]
out = root / "dist"
out.mkdir(exist_ok=True)
excluded = {".git", ".agent", "__pycache__", ".venv", "data", "dist", "qa", "qa_report", ".fonts-src"}
files = sorted(p for p in root.rglob("*") if p.is_file() and not any(part in excluded for part in p.relative_to(root).parts) and p.suffix not in (".pyc", ".docx", ".log", ".sqlite3") and p.name != "ppt-extracted.txt")
with zipfile.ZipFile(out / "gomoku-lab.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for path in files:
        archive.write(path, "gomoku-lab/" + path.relative_to(root).as_posix())
with tarfile.open(out / "gomoku-lab-release.tar.gz", "w:gz") as archive:
    for path in files:
        archive.add(path, arcname=path.relative_to(root).as_posix(), recursive=False)
print(f"Packaged {len(files)} source and deliverable files")
