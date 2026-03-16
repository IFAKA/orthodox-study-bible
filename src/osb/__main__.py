"""Entry point for the Orthodox Study Bible TUI app.

Checks DB state and routes to ImportScreen or MainScreen.

Usage:
    osb                             # default EPUB search
    osb --epub /path/to/osb.epub   # explicit EPUB path
    osb --db-path                   # print DB path and exit
    osb --reimport                  # force re-import even if DB is populated
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def find_epub() -> Path | None:
    """Look for the EPUB in common locations."""
    candidates = [
        Path("data/osb.epub"),
        Path("data/the-orthodox-study-bible.epub"),
        Path("the-orthodox-study-bible.epub"),
        Path.home() / "Downloads" / "orthodox-study-bible.epub",
    ]
    # Also check the directory this script lives in
    here = Path(__file__).parent.parent.parent
    candidates += [
        here / "data" / "osb.epub",
        here / "data" / "the-orthodox-study-bible.epub",
        here / "the-orthodox-study-bible.epub",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Orthodox Study Bible TUI",
        epilog=(
            "Setup: place your OSB EPUB at data/osb.epub (or use --epub), "
            "then run 'osb' — the first launch imports the EPUB automatically.\n\n"
            "Data is stored at: ~/Library/Application Support/osb/  (macOS)\n"
            "                   $XDG_DATA_HOME/osb/                  (Linux)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--epub", type=Path, help="Path to OSB EPUB file")
    parser.add_argument("--db-path", action="store_true", help="Print DB path and exit")
    parser.add_argument("--reimport", action="store_true", help="Force re-import (preserves annotations/bookmarks)")
    parser.add_argument("--reset", action="store_true", help="Clear all personal data (annotations, bookmarks, highlights, chat) but keep scripture")
    parser.add_argument("--uninstall", action="store_true", help="Remove all app data and exit (leaves no trace)")
    args = parser.parse_args()

    from osb.config import APP_DIR, DB_PATH
    from osb.db.migrations import run_migrations
    from osb.db.schema import open_db

    if args.db_path:
        print(DB_PATH)
        return

    if args.uninstall:
        _uninstall(APP_DIR)
        return

    # Ensure app directory exists
    APP_DIR.mkdir(parents=True, exist_ok=True)

    conn = open_db(DB_PATH)
    run_migrations(conn)

    if args.reset:
        _reset_user_data(conn)
        print("Personal data cleared. Run 'osb' to start fresh.")
        conn.close()
        return

    # Determine EPUB path
    epub_path: Path | None = args.epub
    if epub_path is None:
        epub_path = find_epub()

    if args.reimport:
        # Clear import-time tables but preserve user data
        conn.executescript("""
            DELETE FROM verses;
            DELETE FROM chapters;
            DELETE FROM books;
            DELETE FROM commentary;
            DELETE FROM cross_references;
            DELETE FROM verses_fts;
            DELETE FROM commentary_fts;
            DELETE FROM meta WHERE key IN ('epub_sha256', 'import_date');
        """)
        conn.commit()

    from osb.tui.app import OrthodoxStudyApp

    app = OrthodoxStudyApp(conn=conn, epub_path=epub_path)
    app.run()


def _reset_user_data(conn) -> None:
    conn.executescript("""
        DELETE FROM annotations;
        DELETE FROM bookmarks;
        DELETE FROM highlights;
        DELETE FROM reading_progress;
        DELETE FROM chat_history;
        DELETE FROM session;
    """)
    conn.commit()


def _uninstall(app_dir: Path) -> None:
    import shutil

    if not app_dir.exists():
        print("Nothing to remove — app data directory does not exist.")
        return

    answer = input(f"Remove all app data at {app_dir}? This cannot be undone. [y/N] ").strip().lower()
    if answer != "y":
        print("Aborted.")
        return

    shutil.rmtree(app_dir)
    print(f"Removed {app_dir}")
    print("To fully uninstall: pip uninstall orthodox-study-bible  (or remove this project directory)")


if __name__ == "__main__":
    main()
