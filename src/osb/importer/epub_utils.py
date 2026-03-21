"""EPUB parsing utilities: text extraction, verse ID parsing, cleanup."""

import hashlib
import re
from pathlib import Path
from typing import Optional

from bs4 import NavigableString, Tag

# Regex for verse IDs like Gen_vchap1-1, Rom_vchap8-28
VERSE_ID_RE = re.compile(r"^(.+)_vchap(\d+)-(\d+)$")

# Tags whose text we skip entirely
SKIP_CLASSES = {"center", "miniTOC", "footnotedef"}

# CSS classes that carry verse text
VERSE_PARA_CLASSES = {"chapter1", "rindent", "olstyle", "psalm2"}

# CSS classes that carry commentary
COMMENTARY_CLASSES = {"tx", "tx1", "bookstarttxt"}

# Section heading classes
HEADING_CLASSES = {"sub1", "ct", "bookstart"}


def sha256_of_file(path: Path) -> str:
    """Calculate SHA256 hash of file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def get_verse_id(tag: Tag) -> Optional[tuple[str, int, int]]:
    """Extract verse ID from tag. Returns (book_code, chapter, verse) or None."""
    tag_id = tag.get("id", "")
    if not tag_id:
        return None
    m = VERSE_ID_RE.match(tag_id)
    if m:
        return m.group(1), int(m.group(2)), int(m.group(3))
    return None


def clean_text(node) -> str:
    """Extract text from node, stripping footnote superscripts."""
    if isinstance(node, NavigableString):
        return str(node)
    assert isinstance(node, Tag)
    if node.name == "sup":
        if node.get("id") and "_vchap" in node.get("id", ""):
            return ""
        if node.find("a"):
            return ""
        return node.get_text()
    if node.name == "a":
        href = node.get("href", "")
        if "#f" in href or "#fn" in href or "x-liturgical" in href or "study" in href:
            return ""
        return node.get_text()
    return "".join(clean_text(c) for c in node.children)


def extract_text_between_markers(
    para: Tag,
) -> list[tuple[Optional[tuple[str, int, int]], str]]:
    """Parse verse paragraph into [(verse_id, text), ...].

    verse_id is (book_code, chapter, verse) or None for text before any marker.
    """
    events: list[tuple] = []

    container_vid = get_verse_id(para)
    if container_vid:
        events.append(("verse_start", container_vid))

    def walk(node) -> None:
        if isinstance(node, NavigableString):
            events.append(("text", str(node)))
            return
        if not isinstance(node, Tag):
            return

        tag_name = node.name or ""
        cls = node.get("class") or []
        tag_id = node.get("id", "")

        if "chbeg" in cls:
            vid = get_verse_id(node)
            if vid:
                events.append(("verse_start", vid))
            return

        if tag_name == "sup" and "_vchap" in tag_id:
            vid = get_verse_id(node)
            if vid:
                events.append(("verse_start", vid))
            return

        if tag_name == "sup":
            return

        if tag_name == "a":
            href = node.get("href", "")
            if any(k in href for k in ["#f", "study", "x-liturgical", "footnote"]):
                return
            for child in node.children:
                walk(child)
            return

        for child in node.children:
            walk(child)

    walk(para)

    segments: list[tuple[Optional[tuple[str, int, int]], str]] = []
    current_id: Optional[tuple[str, int, int]] = None
    current_text: list[str] = []

    def flush() -> None:
        nonlocal current_text
        text = " ".join("".join(current_text).split()).strip()
        text = re.sub(r"[†ω‡☩✝]+", "", text).strip()
        if text and current_id is not None:
            segments.append((current_id, text))
        current_text = []

    for event_type, value in events:
        if event_type == "verse_start":
            flush()
            current_id = value
        else:
            current_text.append(value)

    flush()
    return segments
