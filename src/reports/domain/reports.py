"""What a report is: a regulator's report, review, roadmap or masterplan. It has no legal force, never a rule.

Its ID is {issuer}:{family}:{edition} for a yearly report (ojk:lpksi:2025), or {issuer}:{family}:{year}:{name}
for one of its kind among others (ojk:roadmap:2023:rp3si): the market contract's pattern.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

ID = re.compile(r"[a-z0-9]+:[a-z0-9]+(:[a-z0-9][a-z0-9._-]*){1,2}")
LPKSI_TITLE = re.compile(r"Laporan Perkembangan Keuangan Syariah Indonesia (\d{4})")
INVISIBLE = re.compile("[\\u200b-\\u200f\\u2060\\ufeff]")  # zero-width characters a CMS leaves in titles


class InvalidReport(ValueError):
    """A report named by hand that doesn't fit the contract."""


@dataclass(frozen=True)
class Report:
    id: str
    issuer: str
    family: str
    edition: str  # as titled: 2025, 2023-2027
    title: str
    published_on: str | None  # ISO date, when known
    language: str

    @classmethod
    def named(
        cls, report_id: str, *, title: str, edition: str, published_on: str | None = None, language: str = "id"
    ) -> Report:
        if report_id != report_id.lower():
            raise InvalidReport(f"{report_id!r}: an ID is lowercase")
        if not ID.fullmatch(report_id):
            raise InvalidReport(f"{report_id!r}: an ID is issuer:family:edition, or issuer:family:year:name")
        issuer, family = report_id.split(":")[:2]
        return cls(report_id, issuer, family, edition, _plain(title), published_on, language)


def lpksi(page_title: str) -> Report | None:
    """OJK's yearly sharia finance report, from its edition page's title; None for any other page."""
    title = _plain(page_title)
    found = LPKSI_TITLE.fullmatch(title)
    if found is None:
        return None
    return Report.named(f"ojk:lpksi:{found[1]}", title=title, edition=found[1])


def _plain(text: str) -> str:
    return " ".join(INVISIBLE.sub("", text).split())
