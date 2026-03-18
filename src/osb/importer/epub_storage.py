"""Database storage and validation for EPUB parser results."""

from collections import Counter
import sqlite3

from osb.db.schema import KNOWN_VERSE_COUNTS


def validate_verses(verses_data: list[dict]) -> list[str]:
    """Validate parsed verse data against known verse counts."""
    counts: Counter = Counter()
    for v in verses_data:
        book = v["chapter_ref"].split("-")[0]
        counts[book] += 1

    warnings_list = []
    for book_abbrev, expected in KNOWN_VERSE_COUNTS.items():
        actual = counts.get(book_abbrev, 0)
        if actual == 0:
            warnings_list.append(f"  {book_abbrev}: MISSING (expected {expected})")
        elif abs(actual - expected) / max(expected, 1) > 0.02:
            pct = (actual - expected) / expected * 100
            warnings_list.append(
                f"  {book_abbrev}: got {actual}, expected {expected} ({pct:+.1f}%)"
            )
    return warnings_list


def write_to_database(
    conn: sqlite3.Connection,
    books_data: list[dict],
    chapters_data: list[dict],
    verses_data: list[dict],
    commentary_data: list[dict],
    glossary_data: list[dict],
) -> None:
    """Write parsed data to SQLite database."""
    conn.executemany(
        "INSERT OR REPLACE INTO books(ref, osb_order, name, testament) "
        "VALUES (:ref, :osb_order, :name, :testament)",
        books_data,
    )
    conn.executemany(
        "INSERT OR REPLACE INTO chapters(ref, book_ref, number) "
        "VALUES (:ref, :book_ref, :number)",
        chapters_data,
    )
    conn.executemany(
        "INSERT OR REPLACE INTO verses(ref, chapter_ref, number, text) "
        "VALUES (:ref, :chapter_ref, :number, :text)",
        verses_data,
    )
    conn.executemany(
        "INSERT INTO commentary(verse_ref, chapter_ref, note_text, note_type) "
        "VALUES (:verse_ref, :chapter_ref, :note_text, :note_type)",
        commentary_data,
    )

    # Populate FTS tables
    conn.executemany(
        "INSERT INTO verses_fts(ref, text) VALUES (:ref, :text)",
        verses_data,
    )
    rows = conn.execute("SELECT id, note_text FROM commentary").fetchall()
    conn.executemany(
        "INSERT INTO commentary_fts(id, note_text) VALUES (?, ?)",
        [(r[0], r[1]) for r in rows],
    )
    if glossary_data:
        conn.executemany(
            "INSERT OR REPLACE INTO glossary(term, definition) VALUES (:term, :definition)",
            glossary_data,
        )
    conn.commit()
