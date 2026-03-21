"""Scripture data queries: books, chapters, verses, commentary, cross-references."""

import sqlite3
from typing import Optional

from osb.models import Book, Chapter, Note, Verse


def get_all_books(conn: sqlite3.Connection) -> list[Book]:
    rows = conn.execute(
        "SELECT ref, osb_order, name, testament FROM books ORDER BY osb_order"
    ).fetchall()
    return [Book(**dict(r)) for r in rows]


def get_book(conn: sqlite3.Connection, ref: str) -> Optional[Book]:
    row = conn.execute(
        "SELECT ref, osb_order, name, testament FROM books WHERE ref=?", (ref,)
    ).fetchone()
    return Book(**dict(row)) if row else None


def get_chapters_for_book(conn: sqlite3.Connection, book_ref: str) -> list[Chapter]:
    rows = conn.execute(
        "SELECT ref, book_ref, number FROM chapters WHERE book_ref=? ORDER BY number",
        (book_ref,),
    ).fetchall()
    return [Chapter(**dict(r)) for r in rows]


def get_chapter(conn: sqlite3.Connection, ref: str) -> Optional[Chapter]:
    row = conn.execute(
        "SELECT ref, book_ref, number FROM chapters WHERE ref=?", (ref,)
    ).fetchone()
    return Chapter(**dict(row)) if row else None


def get_verses_for_chapter(conn: sqlite3.Connection, chapter_ref: str) -> list[Verse]:
    rows = conn.execute(
        "SELECT ref, chapter_ref, number, text FROM verses WHERE chapter_ref=? ORDER BY number",
        (chapter_ref,),
    ).fetchall()
    return [Verse(**dict(r)) for r in rows]


def get_verse(conn: sqlite3.Connection, ref: str) -> Optional[Verse]:
    row = conn.execute(
        "SELECT ref, chapter_ref, number, text FROM verses WHERE ref=?", (ref,)
    ).fetchone()
    return Verse(**dict(row)) if row else None


def get_first_verse_of_chapter(conn: sqlite3.Connection, chapter_ref: str) -> Optional[Verse]:
    row = conn.execute(
        "SELECT ref, chapter_ref, number, text FROM verses WHERE chapter_ref=? ORDER BY number LIMIT 1",
        (chapter_ref,),
    ).fetchone()
    return Verse(**dict(row)) if row else None


def get_last_verse_of_chapter(conn: sqlite3.Connection, chapter_ref: str) -> Optional[Verse]:
    row = conn.execute(
        "SELECT ref, chapter_ref, number, text FROM verses WHERE chapter_ref=? ORDER BY number DESC LIMIT 1",
        (chapter_ref,),
    ).fetchone()
    return Verse(**dict(row)) if row else None


def get_commentary_for_verse(conn: sqlite3.Connection, verse_ref: str) -> list[Note]:
    rows = conn.execute(
        "SELECT id, verse_ref, chapter_ref, note_text, note_type FROM commentary WHERE verse_ref=? ORDER BY id",
        (verse_ref,),
    ).fetchall()
    return [Note(**dict(r)) for r in rows]


def get_commentary_for_chapter(conn: sqlite3.Connection, chapter_ref: str) -> list[Note]:
    rows = conn.execute(
        """SELECT id, verse_ref, chapter_ref, note_text, note_type
           FROM commentary
           WHERE chapter_ref=? AND verse_ref IS NULL
           ORDER BY id""",
        (chapter_ref,),
    ).fetchall()
    return [Note(**dict(r)) for r in rows]


def get_all_commentary_for_chapter(conn: sqlite3.Connection, chapter_ref: str) -> list[Note]:
    """All notes — chapter-level + verse-level — in document order."""
    rows = conn.execute(
        """SELECT c.id, c.verse_ref, c.chapter_ref, c.note_text, c.note_type
           FROM commentary c
           WHERE c.chapter_ref=?
              OR c.verse_ref IN (
                  SELECT ref FROM verses WHERE chapter_ref=?
              )
           ORDER BY c.id""",
        (chapter_ref, chapter_ref),
    ).fetchall()
    return [Note(**dict(r)) for r in rows]


def get_cross_refs(conn: sqlite3.Connection, verse_ref: str) -> list[dict]:
    rows = conn.execute(
        "SELECT from_ref, to_ref_text, to_ref FROM cross_references WHERE from_ref=?",
        (verse_ref,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_verse_refs_with_crossrefs_for_chapter(
    conn: sqlite3.Connection, chapter_ref: str
) -> set[str]:
    rows = conn.execute(
        """SELECT DISTINCT cr.from_ref FROM cross_references cr
           JOIN verses v ON v.ref = cr.from_ref
           WHERE v.chapter_ref = ?""",
        (chapter_ref,),
    ).fetchall()
    return {r[0] for r in rows}


def get_verse_count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) FROM verses").fetchone()
    return row[0] if row else 0
