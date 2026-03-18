"""EPUB parser for the Orthodox Study Bible."""

import logging
import sqlite3
import warnings
from pathlib import Path
from typing import Callable, Optional

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub

from osb.importer.epub_constants import EPUB_CODE_TO_ABBREV, MIN_CONTENT_LENGTH
from osb.importer.epub_parsing import parse_glossary, parse_item_book_abbrev, parse_body
from osb.importer.epub_storage import validate_verses, write_to_database
from osb.importer.epub_utils import sha256_of_file
from osb.importer.structure import get_book_info

warnings.filterwarnings("ignore", category=UserWarning)

logger = logging.getLogger(__name__)


class ParseError(Exception):
    pass


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
        """Extract glossary from EPUB items."""
        self.glossary_data = parse_glossary(self.items)

    def _parse_item(self, name: str, content: bytes) -> None:
        soup = BeautifulSoup(content, "lxml")
        body = soup.find("body")
        if not body:
            return

        abbrev = parse_item_book_abbrev(body)
        if not abbrev:
            return

        if abbrev not in self._inserted_books:
            self._ensure_book(abbrev)

        self._parse_body(body, abbrev)

    def _ensure_book(self, abbrev: str) -> None:
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

    def _parse_body(self, body, abbrev: str) -> None:
        """Extract verses and commentary from body element."""
        verses_data, commentary_data = parse_body(
            body, abbrev,
            self._inserted_books,
            self._inserted_chapters,
            self._inserted_verses,
        )
        self.verses_data.extend(verses_data)
        self.commentary_data.extend(commentary_data)
        # Ensure books are added for any new abbrevs
        for v_ref in self._inserted_verses:
            if "-" in v_ref:
                abbr = v_ref.split("-")[0]
                if abbr not in self._inserted_books and abbr not in [b.get("ref") for b in self.books_data]:
                    self._ensure_book(abbr)

    def resolve_cross_refs(self) -> None:
        """No-op: cross-refs embedded in footnotes; skip for now."""
        pass

    def validate(self) -> list[str]:
        return validate_verses(self.verses_data)

    def write_to_db(self, conn: sqlite3.Connection) -> None:
        write_to_database(
            conn,
            self.books_data,
            self.chapters_data,
            self.verses_data,
            self.commentary_data,
            self.glossary_data,
        )


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
