"""Data model dataclasses."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Book:
    ref: str          # e.g. 'GEN'
    osb_order: int
    name: str
    testament: str    # 'OT', 'NT', 'DC'


@dataclass
class Chapter:
    ref: str          # e.g. 'GEN-1'
    book_ref: str
    number: int


@dataclass
class Verse:
    ref: str          # e.g. 'GEN-1-1'
    chapter_ref: str
    number: int
    text: str


@dataclass
class Note:
    id: int
    verse_ref: Optional[str]
    chapter_ref: Optional[str]
    note_text: str
    note_type: str    # 'inline', 'footnote', 'intro', 'sidebar', 'unclear'


@dataclass
class Annotation:
    verse_ref: str
    body: str
    updated_at: str = ""


@dataclass
class Bookmark:
    verse_ref: str
    label: Optional[str] = None
    created_at: str = ""


@dataclass
class Highlight:
    verse_ref: str
    color: str = "yellow"  # yellow, green, blue, pink


@dataclass
class Collection:
    id: int
    name: str
    created_at: str = ""
    updated_at: str = ""


@dataclass
class CollectionItem:
    id: int
    collection_id: int
    verse_ref: str
    position: int = 0
