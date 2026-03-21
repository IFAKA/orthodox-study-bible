"""Search queries: FTS, chat history, and glossary."""

import re as _re
import sqlite3

_verse_corpus: list[tuple[str, str]] | None = None
_word_index: dict[str, list[str]] | None = None
_corpus_dict: dict[str, str] | None = None


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


def search_glossary(conn: sqlite3.Connection, query: str, limit: int = 50) -> list[dict]:
    like = f"%{query}%"
    rows = conn.execute(
        "SELECT term, definition FROM glossary WHERE term LIKE ? OR definition LIKE ? LIMIT ?",
        (like, like, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def get_glossary_term(conn: sqlite3.Connection, term: str) -> dict | None:
    row = conn.execute(
        "SELECT term, definition FROM glossary WHERE term=?", (term,)
    ).fetchone()
    return dict(row) if row else None
