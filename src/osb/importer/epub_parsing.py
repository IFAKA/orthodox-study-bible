"""EPUB parsing utilities for extracting verses, commentary, and glossary."""

import logging
import re
from bs4 import BeautifulSoup, Tag

from osb.importer.epub_constants import EPUB_CODE_TO_ABBREV
from osb.importer.epub_utils import (
    COMMENTARY_CLASSES,
    HEADING_CLASSES,
    SKIP_CLASSES,
    VERSE_ID_RE,
    VERSE_PARA_CLASSES,
    extract_text_between_markers,
)
from osb.importer.structure import normalize_book_name

logger = logging.getLogger(__name__)


def parse_glossary(items):
    """Scan EPUB items for glossary section and return term/definition pairs."""
    glossary_data = []
    for item in items:
        name = item.get_name().lower()
        if "gloss" not in name and "vocab" not in name:
            continue
        content = item.get_content()
        try:
            soup = BeautifulSoup(content, "lxml")
        except Exception:
            continue
        # Look for definition list structure (dl/dt/dd)
        dts = soup.find_all("dt")
        if dts:
            for dt in dts:
                term = dt.get_text(strip=True)
                dd = dt.find_next_sibling("dd")
                definition = dd.get_text(" ", strip=True) if dd else ""
                if term and definition:
                    glossary_data.append({"term": term, "definition": definition})
            continue
        # Fallback: bold-paragraph pattern
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
                glossary_data.append({"term": term, "definition": definition})
    return glossary_data


def parse_item_book_abbrev(body):
    """Determine book abbreviation from item content."""
    title_tag = body.find("h1", class_="title")
    abbrev = None

    if title_tag:
        book_name = title_tag.get_text(strip=True)
        abbrev = normalize_book_name(book_name)
        if not abbrev:
            clean = re.sub(r"\(.*?\)", "", book_name).strip()
            abbrev = normalize_book_name(clean)

    if not abbrev:
        verse_sup = body.find("sup", id=VERSE_ID_RE)
        if verse_sup:
            m = VERSE_ID_RE.match(verse_sup.get("id", ""))
            if m:
                code = m.group(1)
                abbrev = EPUB_CODE_TO_ABBREV.get(code) or EPUB_CODE_TO_ABBREV.get(code.lower())

    if not abbrev:
        chbeg = body.find("span", class_="chbeg")
        if chbeg:
            m = VERSE_ID_RE.match(chbeg.get("id", ""))
            if m:
                code = m.group(1)
                abbrev = EPUB_CODE_TO_ABBREV.get(code) or EPUB_CODE_TO_ABBREV.get(code.lower())

    return abbrev


def parse_body(body: Tag, abbrev: str, inserted_books, inserted_chapters, inserted_verses):
    """Extract verses and commentary from body element."""
    verses_data, commentary_data = [], []
    current_chapter = None
    last_verse_ref = None

    for tag in body.find_all(["p", "div", "ol"], recursive=True):
        if not isinstance(tag, Tag):
            continue
        cls_set = set(tag.get("class") or [])

        if cls_set & SKIP_CLASSES:
            continue

        if cls_set & VERSE_PARA_CLASSES:
            segments = extract_text_between_markers(tag)
            for vid, text in segments:
                if vid is None:
                    continue
                book_code, ch, v = vid
                eff_abbrev = EPUB_CODE_TO_ABBREV.get(book_code) or EPUB_CODE_TO_ABBREV.get(book_code.lower()) or abbrev
                if eff_abbrev not in inserted_books:
                    inserted_books.add(eff_abbrev)
                ch_ref = f"{eff_abbrev}-{ch}"
                if ch_ref not in inserted_chapters:
                    inserted_chapters.add(ch_ref)
                v_ref = f"{ch_ref}-{v}"
                if v_ref not in inserted_verses and text:
                    verses_data.append({
                        "ref": v_ref,
                        "chapter_ref": ch_ref,
                        "number": v,
                        "text": text,
                    })
                    inserted_verses.add(v_ref)
                    last_verse_ref = v_ref
                    current_chapter = ch
            continue

        if cls_set & COMMENTARY_CLASSES:
            text = tag.get_text(" ", strip=True)
            text = re.sub(r"[†ω‡☩]+", "", text).strip()
            if not text:
                continue
            note_type = "intro" if cls_set & {"bookstarttxt"} else "inline"
            ch_ref = f"{abbrev}-{current_chapter}" if current_chapter else None
            commentary_data.append({
                "verse_ref": last_verse_ref,
                "chapter_ref": ch_ref,
                "note_text": text,
                "note_type": note_type,
            })
            continue

        if cls_set & HEADING_CLASSES:
            text = tag.get_text(" ", strip=True)
            if text and current_chapter:
                ch_ref = f"{abbrev}-{current_chapter}"
                commentary_data.append({
                    "verse_ref": last_verse_ref,
                    "chapter_ref": ch_ref,
                    "note_text": text,
                    "note_type": "sidebar",
                })
            continue

        if tag.name == "div" and "footnotedef" in (tag.get("class") or []):
            text = tag.get_text(" ", strip=True)
            if text and current_chapter:
                ch_ref = f"{abbrev}-{current_chapter}"
                commentary_data.append({
                    "verse_ref": last_verse_ref,
                    "chapter_ref": ch_ref,
                    "note_text": text,
                    "note_type": "footnote",
                })
            continue

    return verses_data, commentary_data
