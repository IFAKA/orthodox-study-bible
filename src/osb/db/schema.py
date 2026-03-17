"""Database schema creation and migration."""

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1

# Expected verse counts per book abbreviation, calibrated against this EPUB.
# Used for post-import validation; allow 2% variance.
# Counts reflect LXX/OSB versification — differ from Protestant (MT) counts.
# Notes:
#   BAR=141: Letter of Jeremiah (Baruch 6) is a separate file mapped to LJE
#   DAN=424: LXX Daniel includes Additions (Susanna + Bel, stored separately as SUS/BEL)
#   PSA=2534: Psalm 151 is included as Ps 151 within the Psalms book
#   4MA/MAN/PS2/3ES/2ES: not present in this EPUB edition
KNOWN_VERSE_COUNTS: dict[str, int] = {
    "GEN": 1533, "EXO": 1171, "LEV": 859, "NUM": 1288, "DEU": 959,
    "JOS": 658, "JDG": 618, "RUT": 85, "1SA": 774, "2SA": 695,
    "1KI": 816, "2KI": 719, "1CH": 942, "2CH": 848, "EZR": 280,
    "NEH": 393, "TOB": 244, "JDT": 340, "EST": 172, "1MA": 924,
    "2MA": 555, "JOB": 1070, "PSA": 2534, "PRO": 955, "ECC": 222,
    "SNG": 117, "WIS": 435, "SIR": 1390, "ISA": 1292, "JER": 1299,
    "BAR": 141, "LAM": 150, "EZK": 1273, "DAN": 424, "HOS": 197,
    "JOL": 73,  "AMO": 146, "OBA": 21,  "JON": 48,  "MIC": 105,
    "NAH": 47,  "HAB": 56,  "ZEP": 53,  "HAG": 38,  "ZEC": 211,
    "MAL": 55,  "MAT": 1071,"MRK": 678, "LUK": 1151,"JHN": 879,
    "ACT": 1007,"ROM": 433, "1CO": 437, "2CO": 257, "GAL": 149,
    "EPH": 155, "PHP": 104, "COL": 95,  "1TH": 89,  "2TH": 47,
    "1TI": 113, "2TI": 83,  "TIT": 46,  "PHM": 25,  "HEB": 303,
    "JAS": 108, "1PE": 105, "2PE": 61,  "1JN": 105, "2JN": 13,
    "3JN": 14,  "JUD": 25,  "REV": 404,
    # Deuterocanonical books present in this EPUB
    "3MA": 227, "1ES": 434, "LJE": 73,  "SUS": 64,  "BEL": 42,
}

DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS books (
    ref         TEXT PRIMARY KEY,
    osb_order   INTEGER NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    testament   TEXT CHECK(testament IN ('OT','NT','DC'))
);

CREATE TABLE IF NOT EXISTS chapters (
    ref         TEXT PRIMARY KEY,
    book_ref    TEXT NOT NULL REFERENCES books(ref),
    number      INTEGER NOT NULL,
    UNIQUE(book_ref, number)
);

CREATE TABLE IF NOT EXISTS verses (
    ref         TEXT PRIMARY KEY,
    chapter_ref TEXT NOT NULL REFERENCES chapters(ref),
    number      INTEGER NOT NULL,
    text        TEXT NOT NULL,
    UNIQUE(chapter_ref, number)
);

CREATE TABLE IF NOT EXISTS commentary (
    id          INTEGER PRIMARY KEY,
    verse_ref   TEXT REFERENCES verses(ref),
    chapter_ref TEXT REFERENCES chapters(ref),
    note_text   TEXT NOT NULL,
    note_type   TEXT CHECK(note_type IN ('inline','footnote','intro','sidebar','unclear'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS verses_fts USING fts5(ref UNINDEXED, text);
CREATE VIRTUAL TABLE IF NOT EXISTS commentary_fts USING fts5(id UNINDEXED, note_text);

CREATE TABLE IF NOT EXISTS cross_references (
    from_ref    TEXT NOT NULL REFERENCES verses(ref),
    to_ref_text TEXT NOT NULL,
    to_ref      TEXT REFERENCES verses(ref)
);

CREATE TABLE IF NOT EXISTS bookmarks (
    verse_ref   TEXT PRIMARY KEY REFERENCES verses(ref),
    label       TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS annotations (
    verse_ref   TEXT PRIMARY KEY REFERENCES verses(ref),
    body        TEXT NOT NULL,
    updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS highlights (
    verse_ref   TEXT PRIMARY KEY REFERENCES verses(ref),
    color       TEXT NOT NULL DEFAULT 'yellow'
    CHECK(color IN ('yellow','green','blue','pink'))
);

CREATE TABLE IF NOT EXISTS reading_progress (
    chapter_ref TEXT PRIMARY KEY REFERENCES chapters(ref),
    completed_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS session (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_history (
    id          INTEGER PRIMARY KEY,
    chapter_ref TEXT NOT NULL,
    role        TEXT CHECK(role IN ('system','user','assistant')),
    content     TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lectionary_menaion (
    month       INTEGER NOT NULL,
    day         INTEGER NOT NULL,
    service     TEXT,
    reading_ref TEXT NOT NULL,
    PRIMARY KEY(month, day, service)
);

CREATE TABLE IF NOT EXISTS lectionary_paschal (
    offset_days INTEGER NOT NULL,
    service     TEXT,
    reading_ref TEXT NOT NULL,
    PRIMARY KEY(offset_days, service)
);

CREATE TABLE IF NOT EXISTS glossary (
    term       TEXT PRIMARY KEY,
    definition TEXT NOT NULL
);
"""


def apply_schema(conn: sqlite3.Connection) -> None:
    """Apply all DDL statements to the database."""
    conn.executescript(DDL)
    conn.execute(
        "INSERT OR IGNORE INTO meta(key, value) VALUES (?, ?)",
        ("schema_version", str(SCHEMA_VERSION)),
    )
    conn.commit()


def open_db(db_path: Path) -> sqlite3.Connection:
    """Open (or create) the SQLite database with schema applied."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    apply_schema(conn)
    return conn
