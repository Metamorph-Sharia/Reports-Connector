"""What a press release is: a regulator's announcement, in its own words, on its date. It has no legal force.

Its ID is {issuer}:siaran-pers:{year}:{name}, the name being its page's, in lower case with only letters and digits
between single hyphens: the market contract's pattern. Numbers aren't keys: OJK's start again each year, and some
releases have none.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

MONTHS = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
    "september": 9, "oktober": 10, "november": 11, "nopember": 11, "desember": 12,
}
LISTED = re.compile(r"(\d{1,2}) ([a-z]+) (\d{4})")
NUMBER = re.compile(r"SP\s*-?\s*\d+\s*/\S.*\d{4}")  # SP 188/DKPU/OJK/X/2026, SP-157/…, SP 60 /…
NUMBER_WITHIN_LINES = 3  # it opens the release, above its title
INVISIBLE = re.compile("[\\u200b-\\u200f\\u2060\\ufeff]")


@dataclass(frozen=True)
class Release:
    id: str
    issuer: str
    number: str | None  # as printed
    title: str  # as listed
    published_on: str  # ISO date, as listed
    language: str = "id"


def release_id(issuer: str, published_on: date, page: str) -> str:
    name = "-".join(re.findall(r"[a-z0-9]+", page.removesuffix(".aspx").lower()))
    return f"{issuer}:siaran-pers:{published_on.year}:{name}"


def listed_date(listed: str) -> date:
    found = LISTED.fullmatch(" ".join(listed.lower().split()))
    if found is None or found[2] not in MONTHS:
        raise ValueError(f"not a date: {listed!r}")
    return date(int(found[3]), MONTHS[found[2]], int(found[1]))


def number(text: str) -> str | None:
    lines = [line for line in (INVISIBLE.sub("", line).strip() for line in text.splitlines()) if line]
    return next((line for line in lines[:NUMBER_WITHIN_LINES] if NUMBER.fullmatch(line)), None)
