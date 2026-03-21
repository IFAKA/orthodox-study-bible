"""User data queries: highlights, bookmarks, annotations, reading progress."""

import sqlite3
from typing import Optional

from osb.models import Annotation, Bookmark, Highlight


HIGHLIGHT_CYCLE = ["yellow", "green", "blue", "pink"]


def get_highlight(conn: sqlite3.Connection, verse_ref: str) -> Optional[Highlight]:
    row = conn.execute(
        "SELECT verse_ref, color FROM highlights WHERE verse_ref=?", (verse_ref,)
    ).fetchone()
    return Highlight(**dict(row)) if row else None


def get_highlights_for_chapter(conn: sqlite3.Connection, chapter_ref: str) -> dict[str, str]:
    """Returns {verse_ref: color} dict."""
    rows = conn.execute(
        """SELECT h.verse_ref, h.color FROM highlights h
           JOIN verses v ON v.ref = h.verse_ref
           WHERE v.chapter_ref=?""",
        (chapter_ref,),
    ).fetchall()
    return {r["verse_ref"]: r["color"] for r in rows}


def cycle_highlight(conn: sqlite3.Connection, verse_ref: str) -> Optional[str]:
    """Cycle color → next; remove if was 'pink'. Returns new color or None."""
    existing = get_highlight(conn, verse_ref)
    if existing is None:
        conn.execute(
            "INSERT INTO highlights(verse_ref, color) VALUES (?, 'yellow')", (verse_ref,)
        )
        conn.commit()
        return "yellow"
    idx = HIGHLIGHT_CYCLE.index(existing.color) if existing.color in HIGHLIGHT_CYCLE else -1
    if idx == len(HIGHLIGHT_CYCLE) - 1:
        conn.execute("DELETE FROM highlights WHERE verse_ref=?", (verse_ref,))
        conn.commit()
        return None
    next_color = HIGHLIGHT_CYCLE[idx + 1]
    conn.execute(
        "UPDATE highlights SET color=? WHERE verse_ref=?", (next_color, verse_ref)
    )
    conn.commit()
    return next_color


def get_bookmark(conn: sqlite3.Connection, verse_ref: str) -> Optional[Bookmark]:
    row = conn.execute(
        "SELECT verse_ref, label, created_at FROM bookmarks WHERE verse_ref=?", (verse_ref,)
    ).fetchone()
    return Bookmark(**dict(row)) if row else None


def toggle_bookmark(conn: sqlite3.Connection, verse_ref: str) -> bool:
    """Returns True if bookmark now exists, False if removed."""
    existing = get_bookmark(conn, verse_ref)
    if existing:
        conn.execute("DELETE FROM bookmarks WHERE verse_ref=?", (verse_ref,))
        conn.commit()
        return False
    conn.execute("INSERT INTO bookmarks(verse_ref) VALUES (?)", (verse_ref,))
    conn.commit()
    return True


def get_all_bookmarks(conn: sqlite3.Connection) -> list[Bookmark]:
    rows = conn.execute(
        "SELECT verse_ref, label, created_at FROM bookmarks ORDER BY created_at DESC"
    ).fetchall()
    return [Bookmark(**dict(r)) for r in rows]


def get_annotation(conn: sqlite3.Connection, verse_ref: str) -> Optional[Annotation]:
    row = conn.execute(
        "SELECT verse_ref, body, updated_at FROM annotations WHERE verse_ref=?", (verse_ref,)
    ).fetchone()
    return Annotation(**dict(row)) if row else None


def save_annotation(conn: sqlite3.Connection, verse_ref: str, body: str) -> None:
    if body.strip():
        conn.execute(
            """INSERT INTO annotations(verse_ref, body, updated_at)
               VALUES (?, ?, datetime('now'))
               ON CONFLICT(verse_ref) DO UPDATE SET body=excluded.body, updated_at=excluded.updated_at""",
            (verse_ref, body),
        )
    else:
        conn.execute("DELETE FROM annotations WHERE verse_ref=?", (verse_ref,))
    conn.commit()


def get_all_annotations(conn: sqlite3.Connection) -> list[Annotation]:
    rows = conn.execute(
        "SELECT verse_ref, body, updated_at FROM annotations ORDER BY updated_at DESC"
    ).fetchall()
    return [Annotation(**dict(r)) for r in rows]


def get_annotated_verse_refs_for_chapter(conn: sqlite3.Connection, chapter_ref: str) -> set[str]:
    rows = conn.execute(
        "SELECT verse_ref FROM annotations WHERE verse_ref IN (SELECT ref FROM verses WHERE chapter_ref=?)",
        (chapter_ref,),
    ).fetchall()
    return {r[0] for r in rows}


def get_bookmarked_verse_refs_for_chapter(conn: sqlite3.Connection, chapter_ref: str) -> set[str]:
    rows = conn.execute(
        "SELECT verse_ref FROM bookmarks WHERE verse_ref IN (SELECT ref FROM verses WHERE chapter_ref=?)",
        (chapter_ref,),
    ).fetchall()
    return {r[0] for r in rows}


def mark_chapter_complete(conn: sqlite3.Connection, chapter_ref: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO reading_progress(chapter_ref) VALUES (?)", (chapter_ref,)
    )
    conn.commit()


def is_chapter_complete(conn: sqlite3.Connection, chapter_ref: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM reading_progress WHERE chapter_ref=?", (chapter_ref,)
    ).fetchone()
    return row is not None


def get_book_completion_pct(conn: sqlite3.Connection, book_ref: str) -> float:
    row = conn.execute(
        """SELECT
               (SELECT COUNT(*) FROM reading_progress rp
                JOIN chapters ch ON ch.ref = rp.chapter_ref
                WHERE ch.book_ref=?) * 1.0 /
               NULLIF((SELECT COUNT(*) FROM chapters WHERE book_ref=?), 0)""",
        (book_ref, book_ref),
    ).fetchone()
    return (row[0] or 0.0) * 100 if row else 0.0


def unmark_chapter_complete(conn: sqlite3.Connection, chapter_ref: str) -> None:
    conn.execute("DELETE FROM reading_progress WHERE chapter_ref=?", (chapter_ref,))
    conn.commit()


def get_total_progress(conn: sqlite3.Connection) -> tuple[int, int]:
    row = conn.execute(
        """SELECT (SELECT COUNT(*) FROM reading_progress),
                  (SELECT COUNT(*) FROM chapters)"""
    ).fetchone()
    return (row[0] or 0, row[1] or 0) if row else (0, 0)


def get_all_books_progress(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """SELECT b.ref, b.name, b.testament, b.osb_order,
                  COUNT(ch.ref) as total,
                  COUNT(rp.chapter_ref) as done
           FROM books b
           JOIN chapters ch ON ch.book_ref = b.ref
           LEFT JOIN reading_progress rp ON rp.chapter_ref = ch.ref
           GROUP BY b.ref ORDER BY b.osb_order"""
    ).fetchall()
    return [dict(r) for r in rows]


def get_first_incomplete_chapter(
    conn: sqlite3.Connection, book_ref: str
) -> Optional[str]:
    """Return first chapter not in reading_progress, or first chapter if all complete."""
    row = conn.execute(
        """SELECT ch.ref FROM chapters ch
           WHERE ch.book_ref = ?
             AND ch.ref NOT IN (SELECT chapter_ref FROM reading_progress)
           ORDER BY ch.number LIMIT 1""",
        (book_ref,),
    ).fetchone()
    if row:
        return row[0]
    row = conn.execute(
        "SELECT ref FROM chapters WHERE book_ref=? ORDER BY number LIMIT 1",
        (book_ref,),
    ).fetchone()
    return row[0] if row else None


def get_session(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM session WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_session(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO session(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    conn.commit()
