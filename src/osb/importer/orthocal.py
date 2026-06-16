"""Fetch daily OCA lectionary readings from orthocal.info.

orthocal.info exposes a JSON API for the OCA daily calendar in both the
Julian (Old Calendar) and Gregorian/Revised-Julian (New Calendar) reckonings:

    https://orthocal.info/api/gregorian/{year}/{month}/{day}/
    https://orthocal.info/api/julian/{year}/{month}/{day}/

We consume only the reading *references* (book/chapter/verse) plus the
commemoration title and fast info — the verse text itself comes from the
app's own OSB database. orthocal's book codes (MAT, ROM, 1CO, ...) already
match this app's verse-ref prefixes, so a reading maps directly to a ref
like "ROM-7-14".
"""

from __future__ import annotations

from datetime import date

import httpx

ORTHOCAL_BASE = "https://orthocal.info/api"

VALID_CALENDARS = ("gregorian", "julian")


def _passage_refs(reading: dict) -> list[str]:
    """Every verse ref in a reading ('ROM-7-14' … 'ROM-8-2').

    orthocal's `passage` lists each verse of the reading (spanning chapters
    and composite ranges), so this yields the full set to navigate to and
    highlight.
    """
    refs: list[str] = []
    for p in reading.get("passage") or []:
        book, chapter, verse = p.get("book"), p.get("chapter"), p.get("verse")
        if book and chapter and verse:
            refs.append(f"{book}-{chapter}-{verse}")
    return refs


def normalize(data: dict, day: date, calendar: str) -> dict:
    """Reduce orthocal's payload to the fields the app renders/stores."""
    readings = []
    for r in data.get("readings", []):
        refs = _passage_refs(r)
        readings.append(
            {
                "source": r.get("source", ""),      # "Epistle", "Gospel", ...
                "display": r.get("display", ""),     # "Romans 7.14-8.2"
                "ref": refs[0] if refs else None,    # first verse, for navigation
                "refs": refs,                        # full range, for highlighting
            }
        )
    return {
        "date": day.isoformat(),
        "calendar": calendar,
        "title": data.get("summary_title") or "",
        "fast": data.get("fast_level_desc") or "",
        "fast_note": data.get("fast_exception_desc") or "",
        "feasts": data.get("feasts") or [],
        "saints": data.get("saints") or [],
        "readings": readings,
    }


def fetch_daily(day: date, calendar: str = "gregorian", timeout: float = 10.0) -> dict | None:
    """Fetch and normalize a day's readings, or None on any failure.

    Network call — run off the UI thread.
    """
    cal = calendar if calendar in VALID_CALENDARS else "gregorian"
    url = f"{ORTHOCAL_BASE}/{cal}/{day.year}/{day.month}/{day.day}/"
    try:
        resp = httpx.get(url, headers={"Accept": "application/json"}, timeout=timeout)
        if resp.status_code != 200:
            return None
        return normalize(resp.json(), day, cal)
    except Exception:
        return None
