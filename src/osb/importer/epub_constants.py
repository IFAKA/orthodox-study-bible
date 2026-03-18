"""Constants for EPUB parsing."""

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

MIN_CONTENT_LENGTH = 200
