"""Build a compressed SQLite DB from the OSB EPUB for distribution.

Usage:
    uv run --extra epub python scripts/build_release_db.py --epub the-orthodox-study-bible.epub

Output:
    dist/osb.db.gz  (with SHA256 printed to stdout)
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

# Ensure src/ is on the path when run from project root
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from osb.db.migrations import run_migrations
from osb.db.schema import open_db
from osb.importer.epub_parser import run_import


def build(epub_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "osb.db"
        conn: sqlite3.Connection = open_db(db_path)
        run_migrations(conn)

        print(f"Importing {epub_path} …")

        def progress_cb(current: int, total: int, message: str) -> None:
            if total > 0:
                pct = int(current / total * 100)
                print(f"  [{pct:3d}%] {message}", end="\r", flush=True)

        sha256, warnings = run_import(epub_path, conn, progress_cb=progress_cb)
        print()  # newline after \r progress

        from datetime import datetime
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            ("epub_sha256", sha256),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            ("import_date", datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()

        if warnings:
            print(f"Warnings ({len(warnings)}):")
            for w in warnings[:20]:
                print(f"  {w}")

        gz_tmp = output_path.with_suffix(".db.gz.tmp")
        print(f"Compressing → {output_path} …")
        with open(db_path, "rb") as f_in, gzip.open(gz_tmp, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        gz_tmp.rename(output_path)

    # Compute SHA256 of compressed file
    h = hashlib.sha256()
    with open(output_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    digest = h.hexdigest()

    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"\nDone: {output_path} ({size_mb:.1f} MB)")
    print(f"SHA256: {digest}")
    print("\nPaste this into src/osb/config.py → DB_RELEASE_SHA256")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build release DB from OSB EPUB")
    parser.add_argument("--epub", required=True, help="Path to the OSB EPUB file")
    parser.add_argument(
        "--output",
        default="dist/osb.db.gz",
        help="Output path (default: dist/osb.db.gz)",
    )
    args = parser.parse_args()

    epub_path = Path(args.epub)
    if not epub_path.exists():
        print(f"ERROR: EPUB not found: {epub_path}", file=sys.stderr)
        sys.exit(1)

    build(epub_path, Path(args.output))


if __name__ == "__main__":
    main()
