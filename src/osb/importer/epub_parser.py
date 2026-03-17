"""EPUB parser for the Orthodox Study Bible.

Structure discovered by epub_inspector.py:
- Each book occupies one or more HTML files (e.g., Genesis.html, Genesis1.html)
- h1.title gives the book name
- Verses are in p.chapter1 and p.rindent paragraphs
- span.chbeg marks chapter starts: id="Gen_vchap1-1" (chapter 1, verse 1)
- sup with id="Gen_vchap1-2" marks subsequent verse starts
- Commentary: p.tx, p.tx1, p.bookstarttxt, p.sub1 (section headings)
- Footnotes: div.footnotedef
"""

import hashlib
import logging
import re
import sqlite3
import warnings
from pathlib import Path
from typing import Callable, Optional

import ebooklib
from bs4 import BeautifulSoup, NavigableString, Tag
from ebooklib import epub

from osb.db.schema import KNOWN_VERSE_COUNTS
from osb.importer.structure import normalize_book_name

# Map from EPUB verse-ID book codes (e.g. "Gen", "K1gdms") to canonical abbrevs.
# Needed for split files that lack an h1.title and for OSB LXX naming.
EPUB_CODE_TO_ABBREV: dict[str, str] = {
    "Gen": "GEN", "Exod": "EXO", "Lev": "LEV", "Num": "NUM", "Deut": "DEU",
    "Josh": "JOS", "Judg": "JDG", "Ruth": "RUT",
    "K1gdms": "1SA", "K2gdms": "2SA", "K3gdms": "1KI", "K4gdms": "2KI",
    "C1hr": "1CH", "C2hr": "2CH", "Ezra": "EZR", "E1sd": "1ES",
    "Neh": "NEH", "Tob": "TOB", "Jdt": "JDT", "Esth": "EST",
    "M1acc": "1MA", "M2acc": "2MA", "M3acc": "3MA",
    "Job": "JOB", "Prov": "PRO", "Eccl": "ECC", "Song": "SNG",
    "Wis": "WIS", "Sir": "SIR",
    "Isa": "ISA", "Jer": "JER", "Lam": "LAM", "Bar": "BAR",
    "Ezek": "EZK", "Dan": "DAN", "Hos": "HOS", "Joel": "JOL",
    "Amos": "AMO", "Jonah": "JON", "Mic": "MIC", "Nah": "NAH",
    "Hab": "HAB", "Zeph": "ZEP", "Hag": "HAG", "zech": "ZEC", "Zech": "ZEC",
    "Mal": "MAL",
    "Matt": "MAT", "Mark": "MRK", "Luke": "LUK", "John": "JHN",
    "Acts": "ACT", "Rom": "ROM", "Ps": "PSA",
    "Sus": "SUS", "Bel": "BEL", "EpJer": "LJE",
    "J2ohn": "2JN", "J3ohn": "3JN", "Jude": "JUD",
    "Phlm": "PHM", "obad": "OBA",
    "C1or": "1CO", "C2or": "2CO", "Gal": "GAL", "Eph": "EPH",
    "Phil": "PHP", "Col": "COL", "T1hess": "1TH", "T2hess": "2TH",
    "T1im": "1TI", "T2im": "2TI", "Titus": "TIT",
    "Heb": "HEB", "Jas": "JAS", "P1et": "1PE", "P2et": "2PE",
    "J1ohn": "1JN", "Rev": "REV",
}

warnings.filterwarnings("ignore", category=UserWarning)

logger = logging.getLogger(__name__)

MIN_CONTENT_LENGTH = 200

# Matches IDs like Gen_vchap1-1, Rom_vchap8-28
VERSE_ID_RE = re.compile(r"^(.+)_vchap(\d+)-(\d+)$")

# Tags whose text we skip entirely (footnote anchors, navigation)
SKIP_CLASSES = {"center", "miniTOC", "footnotedef"}

# CSS classes that carry verse text
# "olstyle" = poetry/verse-per-line books (Proverbs, Job, Psalms, etc.)
# "psalm2"  = psalm superscriptions (verse 1 in LXX)
VERSE_PARA_CLASSES = {"chapter1", "rindent", "olstyle", "psalm2"}

# CSS classes that carry commentary
COMMENTARY_CLASSES = {"tx", "tx1", "bookstarttxt"}

# Section heading classes (stored as sidebar-type commentary)
HEADING_CLASSES = {"sub1", "ct", "bookstart"}


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class ParseError(Exception):
    pass


def _get_verse_id(tag: Tag) -> Optional[tuple[str, int, int]]:
    """If tag has a verse ID, return (book_code, chapter, verse), else None."""
    tag_id = tag.get("id", "")
    if not tag_id:
        return None
    m = VERSE_ID_RE.match(tag_id)
    if m:
        return m.group(1), int(m.group(2)), int(m.group(3))
    return None


def _clean_text(node) -> str:
    """Extract text from a node, stripping footnote superscripts."""
    if isinstance(node, NavigableString):
        return str(node)
    assert isinstance(node, Tag)
    # Skip footnote anchors (sup with href)
    if node.name == "sup":
        # It's a verse marker sup — handled separately, return empty
        if node.get("id") and "_vchap" in node.get("id", ""):
            return ""
        # It's a footnote/liturgical marker — skip
        if node.find("a"):
            return ""
        return node.get_text()
    if node.name == "a":
        # Footnote links — skip their text if they're anchors to footnotes
        href = node.get("href", "")
        if "#f" in href or "#fn" in href or "x-liturgical" in href or "study" in href:
            return ""
        return node.get_text()
    return "".join(_clean_text(c) for c in node.children)


def _extract_text_between_markers(
    para: Tag,
) -> list[tuple[Optional[tuple[str, int, int]], str]]:
    """Parse a verse paragraph into [(verse_id, text), ...].

    Recursively walks the entire paragraph tree so nested verse markers
    (inside kobo span wrappers) are found correctly.
    verse_id is (book_code, chapter, verse) or None for text before any marker.
    """
    events: list[tuple] = []

    # Seed from the container element's own verse ID (e.g. ol.olstyle in Psalms
    # where id="Ps_vchap3-2" sits on the <ol> itself, not on a span.chbeg inside).
    container_vid = _get_verse_id(para)
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

        # span.chbeg — chapter+verse start marker
        if "chbeg" in cls:
            vid = _get_verse_id(node)
            if vid:
                events.append(("verse_start", vid))
            return  # don't emit text from chbeg

        # sup with verse ID — verse marker
        if tag_name == "sup" and "_vchap" in tag_id:
            vid = _get_verse_id(node)
            if vid:
                events.append(("verse_start", vid))
            return  # don't emit text

        # sup without verse ID — footnote/liturgical marker
        if tag_name == "sup":
            return  # skip entirely

        # <a> elements — skip footnote links
        if tag_name == "a":
            href = node.get("href", "")
            if any(k in href for k in ["#f", "study", "x-liturgical", "footnote"]):
                return
            for child in node.children:
                walk(child)
            return

        # All other elements — recurse
        for child in node.children:
            walk(child)

    walk(para)

    # Convert events to segments
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


class OsbEpubParser:
    """Parse OSB EPUB into structured records."""

    def __init__(self, epub_path: Path, progress_cb: Optional[Callable] = None):
        self.epub_path = epub_path
        self.progress_cb = progress_cb or (lambda c, t, m: None)
        self.book: Optional[epub.EpubBook] = None
        self.items: list = []

        self.books_data: list[dict] = []
        self.chapters_data: list[dict] = []
        self.verses_data: list[dict] = []
        self.commentary_data: list[dict] = []
        self.cross_refs_data: list[dict] = []
        self.glossary_data: list[dict] = []

        self._inserted_books: set[str] = set()
        self._inserted_chapters: set[str] = set()
        self._inserted_verses: set[str] = set()

    def load(self) -> str:
        try:
            self.book = epub.read_epub(str(self.epub_path), options={"ignore_ncx": True})
        except Exception as e:
            raise ParseError(
                "EPUB may be DRM-protected. Try removing DRM or using a DRM-free edition."
                if ("DRM" in str(e) or "encrypted" in str(e).lower())
                else f"Failed to read EPUB: {e}"
            ) from e
        self.items = list(self.book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        return sha256_of_file(self.epub_path)

    def parse(self) -> None:
        total = len(self.items)
        for i, item in enumerate(self.items):
            name = item.get_name()
            self.progress_cb(i, total, f"Parsing {name}")
            content = item.get_content()
            if len(content) < MIN_CONTENT_LENGTH:
                continue
            try:
                self._parse_item(name, content)
            except Exception as e:
                logger.error("Error parsing %s: %s", name, e, exc_info=True)
        self._parse_glossary()
        self.progress_cb(total, total, "Parsing complete")

    def _parse_glossary(self) -> None:
        """Scan EPUB items for a glossary section and extract term/definition pairs."""
        for item in self.items:
            name = item.get_name().lower()
            if "gloss" not in name and "vocab" not in name:
                continue
            content = item.get_content()
            try:
                soup = BeautifulSoup(content, "lxml")
            except Exception:
                continue
            # Look for definition list structure (dl/dt/dd) or paragraphs with bold terms
            dts = soup.find_all("dt")
            if dts:
                for dt in dts:
                    term = dt.get_text(strip=True)
                    dd = dt.find_next_sibling("dd")
                    definition = dd.get_text(" ", strip=True) if dd else ""
                    if term and definition:
                        self.glossary_data.append({"term": term, "definition": definition})
                continue
            # Fallback: bold-paragraph pattern (p > b/strong as term, rest as definition)
            for p in soup.find_all("p"):
                bold = p.find(["b", "strong"])
                if not bold:
                    continue
                term = bold.get_text(strip=True)
                if not term:
                    continue
                bold.extract()
                definition = p.get_text(" ", strip=True).lstrip(":— ").strip()
                if definition:
                    self.glossary_data.append({"term": term, "definition": definition})

    def _parse_item(self, name: str, content: bytes) -> None:
        soup = BeautifulSoup(content, "lxml")
        body = soup.find("body")
        if not body:
            return

        # Try h1.title first
        title_tag = body.find("h1", class_="title")
        abbrev: str | None = None

        if title_tag:
            book_name = title_tag.get_text(strip=True)
            abbrev = normalize_book_name(book_name)
            if not abbrev:
                # Try OSB-specific names (e.g. "1 Kingdoms(1 Samuel)")
                # Strip parenthetical
                clean = re.sub(r"\(.*?\)", "", book_name).strip()
                abbrev = normalize_book_name(clean)
            if not abbrev:
                logger.debug("Unrecognized book title %r in %s", book_name, name)

        # Fallback: derive book from first verse sup ID (more reliable than chbeg)
        if not abbrev:
            verse_sup = body.find("sup", id=VERSE_ID_RE)
            if verse_sup:
                m = VERSE_ID_RE.match(verse_sup.get("id", ""))
                if m:
                    code = m.group(1)
                    abbrev = EPUB_CODE_TO_ABBREV.get(code) or EPUB_CODE_TO_ABBREV.get(code.lower())

        # Second fallback: derive from chbeg ID
        if not abbrev:
            chbeg = body.find("span", class_="chbeg")
            if chbeg:
                m = VERSE_ID_RE.match(chbeg.get("id", ""))
                if m:
                    code = m.group(1)
                    abbrev = EPUB_CODE_TO_ABBREV.get(code) or EPUB_CODE_TO_ABBREV.get(code.lower())

        if not abbrev:
            return  # Navigation/intro file with no verse content

        # Ensure book record exists
        if abbrev not in self._inserted_books:
            self._ensure_book(abbrev)

        # Parse content in document order
        self._parse_body(body, abbrev)

    def _ensure_book(self, abbrev: str) -> None:
        from osb.importer.structure import get_book_info
        info = get_book_info(abbrev)
        if info:
            osb_order, abbrev, bname, testament, _ = info
            self.books_data.append({
                "ref": abbrev,
                "osb_order": osb_order,
                "name": bname,
                "testament": testament,
            })
            self._inserted_books.add(abbrev)

    def _ensure_chapter(self, abbrev: str, chapter_num: int) -> str:
        ch_ref = f"{abbrev}-{chapter_num}"
        if ch_ref not in self._inserted_chapters:
            self.chapters_data.append({
                "ref": ch_ref,
                "book_ref": abbrev,
                "number": chapter_num,
            })
            self._inserted_chapters.add(ch_ref)
        return ch_ref

    def _parse_body(self, body: Tag, abbrev: str) -> None:
        """Walk all elements in document order, extract verses and commentary."""
        current_chapter: int | None = None
        last_verse_ref: str | None = None

        for tag in body.find_all(["p", "div", "ol"], recursive=True):
            if not isinstance(tag, Tag):
                continue
            cls_set = set(tag.get("class") or [])

            # Skip nav/skip elements
            if cls_set & SKIP_CLASSES:
                continue

            # Verse paragraphs
            if cls_set & VERSE_PARA_CLASSES:
                segments = _extract_text_between_markers(tag)
                for vid, text in segments:
                    if vid is None:
                        continue
                    book_code, ch, v = vid
                    # Resolve effective abbrev from verse ID's book code
                    eff_abbrev = EPUB_CODE_TO_ABBREV.get(book_code) or EPUB_CODE_TO_ABBREV.get(book_code.lower()) or abbrev
                    if eff_abbrev not in self._inserted_books:
                        self._ensure_book(eff_abbrev)
                    ch_ref = self._ensure_chapter(eff_abbrev, ch)
                    v_ref = f"{ch_ref}-{v}"
                    if v_ref not in self._inserted_verses and text:
                        self.verses_data.append({
                            "ref": v_ref,
                            "chapter_ref": ch_ref,
                            "number": v,
                            "text": text,
                        })
                        self._inserted_verses.add(v_ref)
                        last_verse_ref = v_ref
                        current_chapter = ch
                continue

            # Commentary paragraphs
            if cls_set & COMMENTARY_CLASSES:
                text = tag.get_text(" ", strip=True)
                text = re.sub(r"[†ω‡☩]+", "", text).strip()
                if not text:
                    continue
                if cls_set & {"bookstarttxt"}:
                    note_type = "intro"
                else:
                    note_type = "inline"
                ch_ref = f"{abbrev}-{current_chapter}" if current_chapter else None
                self.commentary_data.append({
                    "verse_ref": last_verse_ref,
                    "chapter_ref": ch_ref,
                    "note_text": text,
                    "note_type": note_type,
                })
                continue

            # Section headings — store as sidebar
            if cls_set & HEADING_CLASSES:
                text = tag.get_text(" ", strip=True)
                if text and current_chapter:
                    ch_ref = f"{abbrev}-{current_chapter}"
                    self.commentary_data.append({
                        "verse_ref": last_verse_ref,
                        "chapter_ref": ch_ref,
                        "note_text": text,
                        "note_type": "sidebar",
                    })
                continue

            # Footnote defs — store as footnote
            if tag.name == "div" and "footnotedef" in (tag.get("class") or []):
                text = tag.get_text(" ", strip=True)
                if text and current_chapter:
                    ch_ref = f"{abbrev}-{current_chapter}"
                    self.commentary_data.append({
                        "verse_ref": last_verse_ref,
                        "chapter_ref": ch_ref,
                        "note_text": text,
                        "note_type": "footnote",
                    })
                continue

    def _parse_element(self, tag, abbrev):
        """Dummy generator to satisfy yield requirement; actual logic is in _parse_body."""
        return
        yield

    def resolve_cross_refs(self) -> None:
        """No-op: cross-refs embedded in footnotes; skip for now."""
        pass

    def validate(self) -> list[str]:
        from collections import Counter
        counts: Counter = Counter()
        for v in self.verses_data:
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

    def write_to_db(self, conn: sqlite3.Connection) -> None:
        conn.executemany(
            "INSERT OR REPLACE INTO books(ref, osb_order, name, testament) "
            "VALUES (:ref, :osb_order, :name, :testament)",
            self.books_data,
        )
        conn.executemany(
            "INSERT OR REPLACE INTO chapters(ref, book_ref, number) "
            "VALUES (:ref, :book_ref, :number)",
            self.chapters_data,
        )
        conn.executemany(
            "INSERT OR REPLACE INTO verses(ref, chapter_ref, number, text) "
            "VALUES (:ref, :chapter_ref, :number, :text)",
            self.verses_data,
        )
        conn.executemany(
            "INSERT INTO commentary(verse_ref, chapter_ref, note_text, note_type) "
            "VALUES (:verse_ref, :chapter_ref, :note_text, :note_type)",
            self.commentary_data,
        )

        # Populate FTS tables
        conn.executemany(
            "INSERT INTO verses_fts(ref, text) VALUES (:ref, :text)",
            self.verses_data,
        )
        # Commentary FTS — need rowids
        rows = conn.execute("SELECT id, note_text FROM commentary").fetchall()
        conn.executemany(
            "INSERT INTO commentary_fts(id, note_text) VALUES (?, ?)",
            [(r[0], r[1]) for r in rows],
        )
        if self.glossary_data:
            conn.executemany(
                "INSERT OR REPLACE INTO glossary(term, definition) VALUES (:term, :definition)",
                self.glossary_data,
            )
        conn.commit()


def run_import(
    epub_path: Path,
    conn: sqlite3.Connection,
    progress_cb: Optional[Callable] = None,
) -> tuple[str, list[str]]:
    """Full import pipeline. Returns (sha256, warnings)."""
    parser = OsbEpubParser(epub_path, progress_cb)
    sha256 = parser.load()
    parser.parse()
    parser.resolve_cross_refs()
    warnings_list = parser.validate()
    parser.write_to_db(conn)
    return sha256, warnings_list
