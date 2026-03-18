"""Typed query functions. All user-data operations use verse ref strings as keys."""

import sqlite3
from typing import Optional

from osb.models import Annotation, Book, Bookmark, Chapter, Collection, CollectionItem, Highlight, Note, Verse


# ── Books ──────────────────────────────────────────────────────────────────────

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


# ── Chapters ──────────────────────────────────────────────────────────────────

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


# ── Verses ────────────────────────────────────────────────────────────────────

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


# ── Commentary ────────────────────────────────────────────────────────────────

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


# ── Cross-references ──────────────────────────────────────────────────────────

def get_cross_refs(conn: sqlite3.Connection, verse_ref: str) -> list[dict]:
    rows = conn.execute(
        "SELECT from_ref, to_ref_text, to_ref FROM cross_references WHERE from_ref=?",
        (verse_ref,),
    ).fetchall()
    return [dict(r) for r in rows]


# ── Highlights ────────────────────────────────────────────────────────────────

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


HIGHLIGHT_CYCLE = ["yellow", "green", "blue", "pink"]


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


# ── Bookmarks ─────────────────────────────────────────────────────────────────

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


# ── Annotations ───────────────────────────────────────────────────────────────

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


# ── Reading progress ──────────────────────────────────────────────────────────

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


# ── Session ───────────────────────────────────────────────────────────────────

def get_session(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM session WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_session(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO session(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    conn.commit()


# ── FTS Search ────────────────────────────────────────────────────────────────

import re as _re

_verse_corpus: list[tuple[str, str]] | None = None
_word_index: dict[str, list[str]] | None = None  # word -> [verse_ref, ...]
_corpus_dict: dict[str, str] | None = None       # verse_ref -> text


def _get_verse_corpus(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    global _verse_corpus
    if _verse_corpus is None:
        rows = conn.execute("SELECT ref, text FROM verses ORDER BY rowid").fetchall()
        _verse_corpus = [(r[0], r[1]) for r in rows]
    return _verse_corpus


def _get_word_index(conn: sqlite3.Connection) -> tuple[dict[str, list[str]], dict[str, str]]:
    global _word_index, _corpus_dict
    if _word_index is None:
        corpus = _get_verse_corpus(conn)
        _word_index = {}
        _corpus_dict = {}
        for ref, text in corpus:
            _corpus_dict[ref] = text
            for w in _re.sub(r"[^\w\s]", "", text.lower()).split():
                _word_index.setdefault(w, []).append(ref)
    return _word_index, _corpus_dict  # type: ignore[return-value]


def fuzzy_search_verses(conn: sqlite3.Connection, query: str, limit: int = 50) -> list[dict]:
    from rapidfuzz import fuzz, process

    query_words = [w for w in _re.sub(r"[^\w\s]", "", query.lower()).split() if len(w) >= 2]
    if not query_words:
        return []

    word_index, corpus_dict = _get_word_index(conn)
    all_words = list(word_index.keys())

    verse_scores: dict[str, float] = {}
    for qw in query_words:
        matches = process.extract(qw, all_words, scorer=fuzz.ratio, limit=30, score_cutoff=65)
        for _matched_word, score, idx in matches:
            matched_word = all_words[idx]
            for ref in word_index[matched_word]:
                if score > verse_scores.get(ref, 0):
                    verse_scores[ref] = score

    sorted_refs = sorted(verse_scores, key=verse_scores.__getitem__, reverse=True)
    return [{"ref": ref, "text": corpus_dict[ref]} for ref in sorted_refs[:limit]]


def search_verses(conn: sqlite3.Connection, query: str, limit: int = 50) -> list[dict]:
    rows = conn.execute(
        """SELECT vf.ref, snippet(verses_fts, 1, '[', ']', '…', 10) AS snippet
           FROM verses_fts vf
           WHERE verses_fts MATCH ?
           ORDER BY rank LIMIT ?""",
        (query, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def search_commentary(conn: sqlite3.Connection, query: str, limit: int = 30) -> list[dict]:
    rows = conn.execute(
        """SELECT cf.id, snippet(commentary_fts, 1, '[', ']', '…', 10) AS snippet
           FROM commentary_fts cf
           WHERE commentary_fts MATCH ?
           ORDER BY rank LIMIT ?""",
        (query, limit),
    ).fetchall()
    return [dict(r) for r in rows]


# ── Chat history ──────────────────────────────────────────────────────────────

def get_chat_history(conn: sqlite3.Connection, chapter_ref: str) -> list[dict]:
    rows = conn.execute(
        """SELECT role, content FROM chat_history
           WHERE chapter_ref=? ORDER BY id""",
        (chapter_ref,),
    ).fetchall()
    return [dict(r) for r in rows]


def append_chat_message(
    conn: sqlite3.Connection, chapter_ref: str, role: str, content: str
) -> None:
    conn.execute(
        "INSERT INTO chat_history(chapter_ref, role, content) VALUES (?, ?, ?)",
        (chapter_ref, role, content),
    )
    conn.commit()


def delete_chat_history(conn: sqlite3.Connection, chapter_ref: str) -> None:
    conn.execute("DELETE FROM chat_history WHERE chapter_ref=?", (chapter_ref,))
    conn.commit()


def get_chapters_with_chat(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT DISTINCT chapter_ref FROM chat_history"
    ).fetchall()
    return {r[0] for r in rows}


# ── Reading progress (extended) ───────────────────────────────────────────────

def unmark_chapter_complete(conn: sqlite3.Connection, chapter_ref: str) -> None:
    conn.execute("DELETE FROM reading_progress WHERE chapter_ref=?", (chapter_ref,))
    conn.commit()


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
    # All complete — return first chapter
    row = conn.execute(
        "SELECT ref FROM chapters WHERE book_ref=? ORDER BY number LIMIT 1",
        (book_ref,),
    ).fetchone()
    return row[0] if row else None


# ── Glossary ──────────────────────────────────────────────────────────────────

def search_glossary(conn: sqlite3.Connection, query: str, limit: int = 50) -> list[dict]:
    like = f"%{query}%"
    rows = conn.execute(
        "SELECT term, definition FROM glossary WHERE term LIKE ? OR definition LIKE ? LIMIT ?",
        (like, like, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def get_glossary_term(conn: sqlite3.Connection, term: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT term, definition FROM glossary WHERE term=?", (term,)
    ).fetchone()
    return dict(row) if row else None


# ── Collections ───────────────────────────────────────────────────────────────

def get_all_collections(conn: sqlite3.Connection) -> list[Collection]:
    rows = conn.execute(
        "SELECT id, name, created_at, updated_at FROM collections ORDER BY updated_at DESC"
    ).fetchall()
    return [Collection(**dict(r)) for r in rows]


def get_collection(conn: sqlite3.Connection, collection_id: int) -> Optional[Collection]:
    row = conn.execute(
        "SELECT id, name, created_at, updated_at FROM collections WHERE id=?", (collection_id,)
    ).fetchone()
    return Collection(**dict(row)) if row else None


def create_collection(conn: sqlite3.Connection, name: str) -> int:
    cur = conn.execute("INSERT INTO collections(name) VALUES (?)", (name,))
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def rename_collection(conn: sqlite3.Connection, collection_id: int, name: str) -> None:
    conn.execute(
        "UPDATE collections SET name=?, updated_at=datetime('now') WHERE id=?",
        (name, collection_id),
    )
    conn.commit()


def delete_collection(conn: sqlite3.Connection, collection_id: int) -> None:
    conn.execute("DELETE FROM collections WHERE id=?", (collection_id,))
    conn.commit()


def get_collection_items(
    conn: sqlite3.Connection, collection_id: int
) -> list[tuple[CollectionItem, Verse]]:
    rows = conn.execute(
        """SELECT ci.id, ci.collection_id, ci.verse_ref, ci.position,
                  v.ref, v.chapter_ref, v.number, v.text
           FROM collection_items ci
           JOIN verses v ON v.ref = ci.verse_ref
           WHERE ci.collection_id=?
           ORDER BY ci.position, ci.id""",
        (collection_id,),
    ).fetchall()
    result = []
    for r in rows:
        item = CollectionItem(
            id=r["id"],
            collection_id=r["collection_id"],
            verse_ref=r["verse_ref"],
            position=r["position"],
        )
        verse = Verse(
            ref=r["ref"],
            chapter_ref=r["chapter_ref"],
            number=r["number"],
            text=r["text"],
        )
        result.append((item, verse))
    return result


def add_verse_to_collection(
    conn: sqlite3.Connection, collection_id: int, verse_ref: str
) -> None:
    row = conn.execute(
        "SELECT MAX(position) FROM collection_items WHERE collection_id=?", (collection_id,)
    ).fetchone()
    next_pos = (row[0] or 0) + 1
    conn.execute(
        "INSERT OR IGNORE INTO collection_items(collection_id, verse_ref, position) VALUES (?, ?, ?)",
        (collection_id, verse_ref, next_pos),
    )
    conn.execute(
        "UPDATE collections SET updated_at=datetime('now') WHERE id=?", (collection_id,)
    )
    conn.commit()


def remove_verse_from_collection(
    conn: sqlite3.Connection, collection_id: int, verse_ref: str
) -> None:
    conn.execute(
        "DELETE FROM collection_items WHERE collection_id=? AND verse_ref=?",
        (collection_id, verse_ref),
    )
    conn.commit()


def reorder_item(
    conn: sqlite3.Connection, collection_id: int, verse_ref: str, direction: int
) -> None:
    """Swap position with adjacent item. direction: +1 = down, -1 = up."""
    rows = conn.execute(
        "SELECT id, verse_ref, position FROM collection_items WHERE collection_id=? ORDER BY position, id",
        (collection_id,),
    ).fetchall()
    refs = [r["verse_ref"] for r in rows]
    if verse_ref not in refs:
        return
    idx = refs.index(verse_ref)
    swap_idx = idx + direction
    if swap_idx < 0 or swap_idx >= len(rows):
        return
    pos_a = rows[idx]["position"]
    pos_b = rows[swap_idx]["position"]
    if pos_a == pos_b:
        pos_b = pos_a + 1
    conn.execute(
        "UPDATE collection_items SET position=? WHERE id=?", (pos_b, rows[idx]["id"])
    )
    conn.execute(
        "UPDATE collection_items SET position=? WHERE id=?", (pos_a, rows[swap_idx]["id"])
    )
    conn.commit()


def get_collections_for_verse(conn: sqlite3.Connection, verse_ref: str) -> list[Collection]:
    rows = conn.execute(
        """SELECT c.id, c.name, c.created_at, c.updated_at
           FROM collections c
           JOIN collection_items ci ON ci.collection_id = c.id
           WHERE ci.verse_ref=?
           ORDER BY c.updated_at DESC""",
        (verse_ref,),
    ).fetchall()
    return [Collection(**dict(r)) for r in rows]


def get_collection_item_count(conn: sqlite3.Connection, collection_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM collection_items WHERE collection_id=?", (collection_id,)
    ).fetchone()
    return row[0] if row else 0


# ── Meta ──────────────────────────────────────────────────────────────────────

def get_verse_count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) FROM verses").fetchone()
    return row[0] if row else 0
