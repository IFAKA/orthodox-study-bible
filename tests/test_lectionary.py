"""Tests for the daily lectionary fetch/normalize/cache layer.

These are network-free: orthocal.normalize and the cache helpers are pure /
local, and get_readings is exercised via a pre-seeded cache with fetching
disabled.
"""

from __future__ import annotations

import json
from datetime import date

from osb.db.schema import open_db
from osb.importer import lectionary, orthocal

# A trimmed sample of an orthocal.info JSON payload.
SAMPLE = {
    "summary_title": "St Tycho, Bishop of Amathus",
    "fast_level_desc": "Apostles Fast",
    "fast_exception_desc": "Wine and Oil are Allowed",
    "feasts": [],
    "saints": ["St Tycho"],
    "readings": [
        {
            "source": "Epistle",
            "display": "Romans 7.14-8.2",
            "passage": [{"book": "ROM", "chapter": 7, "verse": 14, "content": "..."}],
        },
        {
            "source": "Gospel",
            "display": "Matthew 10.9-15",
            "passage": [{"book": "MAT", "chapter": 10, "verse": 9, "content": "..."}],
        },
    ],
}


def test_passage_to_ref_builds_navigable_ref():
    assert orthocal._passage_to_ref(SAMPLE["readings"][0]) == "ROM-7-14"
    assert orthocal._passage_to_ref(SAMPLE["readings"][1]) == "MAT-10-9"


def test_passage_to_ref_handles_empty():
    assert orthocal._passage_to_ref({"passage": []}) is None
    assert orthocal._passage_to_ref({}) is None
    assert orthocal._passage_to_ref({"passage": [{"book": "ROM"}]}) is None


def test_normalize_shape():
    out = orthocal.normalize(SAMPLE, date(2026, 6, 16), "gregorian")
    assert out["date"] == "2026-06-16"
    assert out["calendar"] == "gregorian"
    assert out["title"] == "St Tycho, Bishop of Amathus"
    assert out["fast"] == "Apostles Fast"
    assert out["fast_note"] == "Wine and Oil are Allowed"
    assert [r["source"] for r in out["readings"]] == ["Epistle", "Gospel"]
    assert out["readings"][0]["ref"] == "ROM-7-14"
    # The verse text is intentionally dropped (app uses its own OSB text).
    assert "content" not in out["readings"][0]


def test_cache_round_trip(tmp_path):
    from osb.db import queries

    conn = open_db(tmp_path / "t.db")
    assert queries.get_lectionary_cache(conn, "2026-06-16", "gregorian") is None
    queries.set_lectionary_cache(conn, "2026-06-16", "gregorian", '{"hi": 1}')
    assert queries.get_lectionary_cache(conn, "2026-06-16", "gregorian") == '{"hi": 1}'
    # Different calendar is a separate row.
    assert queries.get_lectionary_cache(conn, "2026-06-16", "julian") is None
    conn.close()


def test_get_readings_uses_cache_without_fetching(tmp_path):
    from osb.db import queries

    conn = open_db(tmp_path / "t.db")
    payload = orthocal.normalize(SAMPLE, date(2026, 6, 16), "gregorian")
    queries.set_lectionary_cache(conn, "2026-06-16", "gregorian", json.dumps(payload))

    # allow_fetch=False guarantees no network is attempted.
    out = lectionary.get_readings(conn, date(2026, 6, 16), "gregorian", allow_fetch=False)
    assert out is not None
    assert out["title"] == "St Tycho, Bishop of Amathus"
    assert out["readings"][1]["ref"] == "MAT-10-9"

    # Cache miss + no fetch -> None.
    assert lectionary.get_readings(conn, date(2026, 6, 17), "gregorian", allow_fetch=False) is None
    conn.close()
