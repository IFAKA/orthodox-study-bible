"""Orthodox 76-book canon: abbreviations, ordering, name normalization."""

from dataclasses import dataclass
from typing import Optional

# (osb_order, abbrev, canonical_name, testament, alt_names...)
# testament: OT=Old Testament, NT=New Testament, DC=Deuterocanonical
CANON: list[tuple] = [
    # Old Testament
    (1,  "GEN", "Genesis",                  "OT", ["genesis", "gen"]),
    (2,  "EXO", "Exodus",                   "OT", ["exodus", "exo", "ex"]),
    (3,  "LEV", "Leviticus",                "OT", ["leviticus", "lev"]),
    (4,  "NUM", "Numbers",                  "OT", ["numbers", "num"]),
    (5,  "DEU", "Deuteronomy",              "OT", ["deuteronomy", "deu", "deut"]),
    (6,  "JOS", "Joshua",                   "OT", ["joshua", "jos", "josh"]),
    (7,  "JDG", "Judges",                   "OT", ["judges", "jdg", "judg"]),
    (8,  "RUT", "Ruth",                     "OT", ["ruth", "rut"]),
    (9,  "1SA", "1 Samuel",                 "OT", ["1 samuel", "1sam", "1sa", "1 sam", "1 kingdoms", "1kingdoms", "1 kingdoms(1 samuel)"]),
    (10, "2SA", "2 Samuel",                 "OT", ["2 samuel", "2sam", "2sa", "2 sam", "2 kingdoms", "2kingdoms", "2 kingdoms(2 samuel)"]),
    (11, "1KI", "1 Kings",                  "OT", ["1 kings", "1ki", "1kgs", "1 kgs", "3 kingdoms", "3kingdoms", "3 kingdoms(1 kings)"]),
    (12, "2KI", "2 Kings",                  "OT", ["2 kings", "2ki", "2kgs", "2 kgs", "4 kingdoms", "4kingdoms", "4 kingdoms(2 kings)"]),
    (13, "1CH", "1 Chronicles",             "OT", ["1 chronicles", "1ch", "1chr", "1 chr"]),
    (14, "2CH", "2 Chronicles",             "OT", ["2 chronicles", "2ch", "2chr", "2 chr"]),
    (15, "EZR", "Ezra",                     "OT", ["ezra", "ezr"]),
    (16, "NEH", "Nehemiah",                 "OT", ["nehemiah", "neh"]),
    (17, "TOB", "Tobit",                    "DC", ["tobit", "tob"]),
    (18, "JDT", "Judith",                   "DC", ["judith", "jdt", "jth"]),
    (19, "EST", "Esther",                   "OT", ["esther", "est", "esth"]),
    (20, "1MA", "1 Maccabees",              "DC", ["1 maccabees", "1ma", "1macc", "1 macc"]),
    (21, "2MA", "2 Maccabees",              "DC", ["2 maccabees", "2ma", "2macc", "2 macc"]),
    (22, "3MA", "3 Maccabees",              "DC", ["3 maccabees", "3ma", "3macc"]),
    (23, "4MA", "4 Maccabees",              "DC", ["4 maccabees", "4ma", "4macc"]),
    (24, "JOB", "Job",                      "OT", ["job"]),
    (25, "PSA", "Psalms",                   "OT", ["psalms", "psa", "ps", "psalm"]),
    (26, "PS2", "Prayer of Manasseh",       "DC", ["prayer of manasseh", "ps2", "man", "pman"]),
    (27, "PRO", "Proverbs",                 "OT", ["proverbs", "pro", "prov", "proverbs of solomon"]),
    (28, "ECC", "Ecclesiastes",             "OT", ["ecclesiastes", "ecc", "eccl", "qoh"]),
    (29, "SNG", "Song of Songs",            "OT", ["song of songs", "sng", "song", "sol", "ss"]),
    (30, "WIS", "Wisdom of Solomon",        "DC", ["wisdom", "wis", "wisd"]),
    (31, "SIR", "Sirach",                   "DC", ["sirach", "sir", "ecclesiasticus", "ecclus", "wisdom of sirach"]),
    (32, "ISA", "Isaiah",                   "OT", ["isaiah", "isa"]),
    (33, "JER", "Jeremiah",                 "OT", ["jeremiah", "jer"]),
    (34, "LAM", "Lamentations",             "OT", ["lamentations", "lam", "lamentations of jeremiah"]),
    (35, "BAR", "Baruch",                   "DC", ["baruch", "bar"]),
    (36, "LJE", "Letter of Jeremiah",       "DC", ["letter of jeremiah", "lje", "epjer", "epistle of jeremiah"]),
    (37, "EZK", "Ezekiel",                  "OT", ["ezekiel", "ezk", "ezek"]),
    (38, "DAN", "Daniel",                   "OT", ["daniel", "dan"]),
    (39, "SUS", "Susanna",                  "DC", ["susanna", "sus"]),
    (40, "BEL", "Bel and the Dragon",       "DC", ["bel and the dragon", "bel"]),
    (41, "HOS", "Hosea",                    "OT", ["hosea", "hos"]),
    (42, "JOL", "Joel",                     "OT", ["joel", "jol", "joe"]),
    (43, "AMO", "Amos",                     "OT", ["amos", "amo", "am"]),
    (44, "OBA", "Obadiah",                  "OT", ["obadiah", "oba", "obad"]),
    (45, "JON", "Jonah",                    "OT", ["jonah", "jon"]),
    (46, "MIC", "Micah",                    "OT", ["micah", "mic"]),
    (47, "NAH", "Nahum",                    "OT", ["nahum", "nah"]),
    (48, "HAB", "Habakkuk",                 "OT", ["habakkuk", "hab"]),
    (49, "ZEP", "Zephaniah",               "OT", ["zephaniah", "zep", "zeph"]),
    (50, "HAG", "Haggai",                   "OT", ["haggai", "hag"]),
    (51, "ZEC", "Zechariah",               "OT", ["zechariah", "zec", "zech"]),
    (52, "MAL", "Malachi",                  "OT", ["malachi", "mal"]),
    (53, "1ES", "1 Esdras",                 "DC", ["1 esdras", "1es", "1esd"]),
    (54, "2ES", "2 Esdras",                 "DC", ["2 esdras", "2es", "2esd"]),
    (55, "3ES", "3 Esdras",                 "DC", ["3 esdras", "3es", "3esd"]),
    (56, "MAN", "Prayer of Manasseh",       "DC", ["prayer of manasseh"]),
    # New Testament
    (57, "MAT", "Matthew",                  "NT", ["matthew", "mat", "matt"]),
    (58, "MRK", "Mark",                     "NT", ["mark", "mrk", "mar"]),
    (59, "LUK", "Luke",                     "NT", ["luke", "luk"]),
    (60, "JHN", "John",                     "NT", ["john", "jhn", "jn"]),
    (61, "ACT", "Acts",                     "NT", ["acts", "act"]),
    (62, "ROM", "Romans",                   "NT", ["romans", "rom"]),
    (63, "1CO", "1 Corinthians",            "NT", ["1 corinthians", "1co", "1cor", "1 cor"]),
    (64, "2CO", "2 Corinthians",            "NT", ["2 corinthians", "2co", "2cor", "2 cor"]),
    (65, "GAL", "Galatians",                "NT", ["galatians", "gal"]),
    (66, "EPH", "Ephesians",                "NT", ["ephesians", "eph"]),
    (67, "PHP", "Philippians",              "NT", ["philippians", "php", "phil"]),
    (68, "COL", "Colossians",               "NT", ["colossians", "col"]),
    (69, "1TH", "1 Thessalonians",          "NT", ["1 thessalonians", "1th", "1thes", "1 thes"]),
    (70, "2TH", "2 Thessalonians",          "NT", ["2 thessalonians", "2th", "2thes", "2 thes"]),
    (71, "1TI", "1 Timothy",                "NT", ["1 timothy", "1ti", "1tim", "1 tim"]),
    (72, "2TI", "2 Timothy",                "NT", ["2 timothy", "2ti", "2tim", "2 tim"]),
    (73, "TIT", "Titus",                    "NT", ["titus", "tit"]),
    (74, "PHM", "Philemon",                 "NT", ["philemon", "phm", "phlm"]),
    (75, "HEB", "Hebrews",                  "NT", ["hebrews", "heb"]),
    (76, "JAS", "James",                    "NT", ["james", "jas", "jam"]),
    (77, "1PE", "1 Peter",                  "NT", ["1 peter", "1pe", "1pet", "1 pet"]),
    (78, "2PE", "2 Peter",                  "NT", ["2 peter", "2pe", "2pet", "2 pet"]),
    (79, "1JN", "1 John",                   "NT", ["1 john", "1jn", "1joh", "1 joh"]),
    (80, "2JN", "2 John",                   "NT", ["2 john", "2jn", "2joh"]),
    (81, "3JN", "3 John",                   "NT", ["3 john", "3jn", "3joh"]),
    (82, "JUD", "Jude",                     "NT", ["jude", "jud"]),
    (83, "REV", "Revelation",               "NT", ["revelation", "rev", "apoc", "apocalypse"]),
]

# Build lookup tables
_by_abbrev: dict[str, tuple] = {}
_by_name_lower: dict[str, str] = {}  # normalized name → abbrev

for _entry in CANON:
    _osb_order, _abbrev, _name, _testament, _alts = _entry
    _by_abbrev[_abbrev] = _entry
    for _alt in _alts:
        _by_name_lower[_alt.lower()] = _abbrev
    _by_name_lower[_name.lower()] = _abbrev
    _by_name_lower[_abbrev.lower()] = _abbrev


def normalize_book_name(name: str) -> Optional[str]:
    """Return canonical abbreviation for a book name/abbreviation, or None."""
    return _by_name_lower.get(name.strip().lower())


def get_book_info(abbrev: str) -> Optional[tuple]:
    """Return (osb_order, abbrev, name, testament, alts) or None."""
    return _by_abbrev.get(abbrev.upper())


def all_book_abbrevs() -> list[str]:
    """All abbreviations in OSB canonical order."""
    return [e[1] for e in sorted(CANON, key=lambda x: x[0])]


def format_ref(ref: str) -> str:
    """Convert internal ref to human-readable string.

    'GEN-1-1'  → 'Genesis 1:1'
    'GEN-1'    → 'Genesis 1'
    'GEN'      → 'Genesis'
    """
    parts = ref.split("-")
    info = get_book_info(parts[0])
    name = info[2] if info else parts[0]
    if len(parts) == 3:
        return f"{name} {parts[1]}:{parts[2]}"
    if len(parts) == 2:
        return f"{name} {parts[1]}"
    return name
