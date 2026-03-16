"""Parser regression tests against the golden snapshot.

Run:  pytest tests/test_parser.py
Requires the EPUB at the project root (not committed to git).
Tests are skipped automatically if the file is absent.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

EPUB_PATH = Path(__file__).parent.parent / "the-orthodox-study-bible.epub"
GOLDEN_PATH = Path(__file__).parent / "golden.json"

pytestmark = pytest.mark.skipif(
    not EPUB_PATH.exists(), reason="EPUB file not present"
)


@pytest.fixture(scope="module")
def parsed():
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from osb.importer.epub_parser import OsbEpubParser

    p = OsbEpubParser(EPUB_PATH)
    p.load()
    p.parse()
    return p


@pytest.fixture(scope="module")
def golden():
    return json.loads(GOLDEN_PATH.read_text())


def test_total_verse_count(parsed, golden):
    assert len(parsed.verses_data) == golden["total_verses"]


def test_total_book_count(parsed, golden):
    assert len(parsed.books_data) == golden["total_books"]


def test_per_book_verse_counts(parsed, golden):
    counts: dict[str, int] = {}
    for v in parsed.verses_data:
        book = v["chapter_ref"].split("-")[0]
        counts[book] = counts.get(book, 0) + 1

    failures = []
    for book, expected in golden["verse_counts"].items():
        actual = counts.get(book, 0)
        if actual != expected:
            failures.append(f"{book}: got {actual}, expected {expected}")

    assert not failures, "Verse count regressions:\n" + "\n".join(failures)


def test_sample_verse_text(parsed, golden):
    verse_map = {v["ref"]: v["text"] for v in parsed.verses_data}

    failures = []
    for book, verses in golden["samples"].items():
        for sample in verses:
            actual = verse_map.get(sample["ref"])
            if actual != sample["text"]:
                failures.append(
                    f'{sample["ref"]}:\n  expected: {sample["text"]!r}\n  got:      {actual!r}'
                )

    assert not failures, "Verse text regressions:\n\n" + "\n\n".join(failures)


def test_no_validation_warnings(parsed):
    warnings = parsed.validate()
    assert warnings == [], "Unexpected validation warnings:\n" + "\n".join(warnings)
