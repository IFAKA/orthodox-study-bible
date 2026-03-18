"""Lectionary engine.

Computes the daily Orthodox reading from:
1. Menaion (fixed calendar, by month+day)
2. Paschal cycle (moveable feasts, offset from Pascha)
"""

from __future__ import annotations

import math
from datetime import date, timedelta


def julian_pascha(year: int) -> date:
    """Compute Julian calendar Pascha (Easter) for the given year, return as Gregorian date.

    Uses the Meeus Julian algorithm.
    Julian-to-Gregorian offset for 20th/21st century is +13 days.
    """
    a = year % 4
    b = year % 7
    c = year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    month = math.floor((d + e + 114) / 31)
    day = ((d + e + 114) % 31) + 1

    julian = date(year, month, day)
    # Julian to Gregorian: add 13 days for years 1900–2099
    gregorian = julian + timedelta(days=13)
    return gregorian


def get_paschal_offset(today: date) -> int:
    """Return days offset from this year's Pascha. Negative = before Pascha."""
    pascha = julian_pascha(today.year)
    delta = (today - pascha).days
    # If we're past this year's Pascha by a lot, check next year's
    if delta > 200:
        pascha_next = julian_pascha(today.year + 1)
        delta_next = (today - pascha_next).days
        if abs(delta_next) < abs(delta):
            return delta_next
    return delta


# ── Sample Menaion (fixed calendar) ──────────────────────────────────────────
# Format: (month, day, service, reading_ref, feast_name)
# reading_ref uses canonical verse refs e.g. "MAT-5-1"
# This is a minimal seed; a full Menaion has hundreds of entries.
MENAION_DATA: list[tuple[int, int, str, str, str]] = [
    (1,  1,  "matins",  "LUK-2-21",   "Circumcision of Christ"),
    (1,  6,  "matins",  "MAT-3-13",   "Theophany"),
    (1,  7,  "matins",  "JHN-1-29",   "Synaxis of John the Baptist"),
    (1,  14, "matins",  "MAT-4-1",    "Sunday after Theophany"),
    (2,  2,  "matins",  "LUK-2-22",   "Meeting of the Lord"),
    (2,  14, "matins",  "JHN-15-9",   "Saints Cyril & Methodius"),
    (3,  25, "matins",  "LUK-1-26",   "Annunciation"),
    (4,  23, "matins",  "JHN-15-17",  "Great Martyr George"),
    (5,  21, "matins",  "JHN-17-1",   "Ss. Constantine & Helen"),
    (6,  24, "matins",  "LUK-1-57",   "Nativity of John the Baptist"),
    (6,  29, "matins",  "MAT-16-13",  "Ss. Peter & Paul"),
    (7,  20, "matins",  "MRK-6-14",   "Prophet Elijah"),
    (8,  6,  "matins",  "MAT-17-1",   "Transfiguration"),
    (8,  15, "matins",  "LUK-10-38",  "Dormition of the Theotokos"),
    (8,  29, "matins",  "MRK-6-17",   "Beheading of John the Baptist"),
    (9,  8,  "matins",  "LUK-1-39",   "Nativity of the Theotokos"),
    (9,  14, "matins",  "JHN-12-28",  "Exaltation of the Holy Cross"),
    (10, 1,  "matins",  "LUK-10-16",  "Protection of the Theotokos"),
    (10, 14, "matins",  "LUK-10-1",   "Ss. Cosmas & Damian"),
    (11, 21, "matins",  "LUK-10-38",  "Entrance of the Theotokos"),
    (12, 6,  "matins",  "LUK-6-17",   "St. Nicholas"),
    (12, 25, "matins",  "MAT-2-1",    "Nativity of Christ"),
    (12, 25, "liturgy", "GAL-4-4",    "Nativity of Christ"),
]

# ── Sample Paschal cycle ──────────────────────────────────────────────────────
# offset_days from Pascha (0 = Pascha Sunday)
PASCHAL_DATA: list[tuple[int, str, str, str]] = [
    (-70, "matins",  "LUK-18-10", "Sunday of the Publican & Pharisee"),
    (-63, "matins",  "LUK-15-11", "Sunday of the Prodigal Son"),
    (-56, "matins",  "MAT-25-31", "Meatfare Sunday"),
    (-49, "matins",  "MAT-6-14",  "Cheesefare Sunday"),
    (-48, "matins",  "MAT-6-1",   "Clean Monday"),
    (-42, "matins",  "MAT-17-1",  "Sunday of Orthodoxy"),
    (-35, "matins",  "MRK-2-1",   "2nd Sunday of Lent"),
    (-28, "matins",  "MRK-8-34",  "Sunday of the Holy Cross"),
    (-21, "matins",  "JHN-11-1",  "4th Sunday of Lent"),
    (-14, "matins",  "MRK-10-32", "5th Sunday of Lent"),
    (-7,  "matins",  "JHN-12-1",  "Palm Sunday"),
    (-6,  "matins",  "MAT-21-18", "Holy Monday"),
    (-5,  "matins",  "JHN-12-17", "Holy Tuesday"),
    (-4,  "matins",  "MAT-26-6",  "Holy Wednesday"),
    (-3,  "matins",  "JHN-13-1",  "Holy Thursday"),
    (-2,  "matins",  "JHN-18-1",  "Holy Friday"),
    (-1,  "matins",  "MAT-28-1",  "Holy Saturday"),
    (0,   "matins",  "JHN-20-1",  "Holy Pascha"),
    (7,   "matins",  "JHN-20-19", "Thomas Sunday"),
    (14,  "matins",  "JHN-5-1",   "Sunday of the Myrrh-bearers"),
    (21,  "matins",  "JHN-4-5",   "Sunday of the Paralytic"),
    (28,  "matins",  "JHN-5-1",   "Sunday of the Samaritan Woman"),
    (35,  "matins",  "JHN-9-1",   "Sunday of the Blind Man"),
    (39,  "matins",  "ACT-1-1",   "Ascension"),
    (42,  "matins",  "JHN-17-1",  "Sunday of the Holy Fathers"),
    (49,  "matins",  "ACT-2-1",   "Pentecost"),
    (56,  "matins",  "MAT-18-10", "All Saints Sunday"),
]


def get_daily_readings(today: date | None = None) -> list[dict]:
    """Return list of {service, reading_ref, source, feast_name} for today."""
    if today is None:
        today = date.today()

    readings = []

    # Menaion readings for today
    for month, day, service, ref, feast_name in MENAION_DATA:
        if month == today.month and day == today.day:
            readings.append({
                "service": service,
                "reading_ref": ref,
                "source": "menaion",
                "feast_name": feast_name,
            })

    # Paschal readings
    offset = get_paschal_offset(today)
    for offset_days, service, ref, feast_name in PASCHAL_DATA:
        if offset_days == offset:
            readings.append({
                "service": service,
                "reading_ref": ref,
                "source": "paschal",
                "feast_name": feast_name,
            })

    return readings



def get_primary_feast(today: date | None = None) -> tuple[str, str | None] | None:
    """Return (reading_ref, feast_name) for the primary reading today, or None."""
    if today is None:
        today = date.today()
    readings = get_daily_readings(today)
    paschal = [r for r in readings if r["source"] == "paschal"]
    primary = paschal[0] if paschal else (readings[0] if readings else None)
    if primary:
        return primary["reading_ref"], primary.get("feast_name")
    return None
