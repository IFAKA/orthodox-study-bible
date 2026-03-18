"""Utilities for chat processing."""

import re
import sqlite3

from osb.db import queries
from osb.importer.structure import normalize_book_name


def parse_refs(text: str, conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """Return deduplicated (verse_ref, display_label) list extracted from AI text."""
    pattern = re.compile(
        r'(?<!\w)(\d?\s*[A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(\d+):(\d+)(?:-\d+)?(?!\d)'
    )
    seen: set[str] = set()
    results: list[tuple[str, str]] = []
    for m in pattern.finditer(text):
        book_raw, chapter, verse = m.group(1).strip(), m.group(2), m.group(3)
        abbrev = normalize_book_name(book_raw)
        if not abbrev:
            continue
        verse_ref = f"{abbrev}-{chapter}-{verse}"
        if verse_ref in seen:
            continue
        if queries.get_verse(conn, verse_ref) is None:
            continue
        seen.add(verse_ref)
        results.append((verse_ref, f"{book_raw.title()} {chapter}:{verse}"))
    return results
