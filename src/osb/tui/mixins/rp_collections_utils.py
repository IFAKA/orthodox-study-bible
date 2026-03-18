"""Utilities for collections rendering and input handling."""

import re
import sqlite3

from osb.db import queries
from osb.importer.structure import normalize_book_name


def build_collection_label(col_name: str, item_count: int) -> str:
    """Build a label for a collection list item."""
    return f"{col_name}  [dim]({item_count})[/]"


def build_detail_header(col_name: str, total_items: int) -> str:
    """Build the header label for collection detail view."""
    return f"[dim]Collections /[/] {col_name}  [dim]{total_items}[/]"


def build_detail_hints() -> str:
    """Get the hint text for collection detail view."""
    return "[dim]↵ jump  ·  a add  ·  x remove  ·  J/K reorder  ·  r rename  ·  Esc ← list[/]"


def build_list_hints(has_temp: bool) -> str:
    """Get the hint text for collections list view."""
    parts = ["↵ open", "n new", "r rename", "d delete"]
    if has_temp:
        parts.append("s save")
    return "[dim]" + "  ·  ".join(parts) + "[/]"


def make_chapter_prefix(conn: sqlite3.Connection, chapter_ref: str) -> str:
    """Build chapter prefix from chapter_ref for collection naming."""
    parts = chapter_ref.split("-")
    if len(parts) >= 2:
        book = queries.get_book(conn, parts[0])
        book_name = book.name if book else parts[0]
        return f"{book_name} {parts[1]}"
    return chapter_ref


def parse_verse_input(conn: sqlite3.Connection, text: str) -> str | None:
    """Parse verse reference from user input, validating it exists."""
    m = re.match(r'^\s*(\d?\s*[A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(\d+):(\d+)\s*$', text.strip())
    if not m:
        return None
    book_raw, chapter, verse = m.group(1).strip(), m.group(2), m.group(3)
    abbrev = normalize_book_name(book_raw)
    if not abbrev:
        return None
    verse_ref = f"{abbrev}-{chapter}-{verse}"
    return verse_ref if queries.get_verse(conn, verse_ref) is not None else None
