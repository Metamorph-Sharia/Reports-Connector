"""What the use cases need from outside: OJK's LPKSI listing and press releases, something that reads a PDF's text,
somewhere to keep reports and releases, and something that writes a bundle. Each port has a real adapter and an
in-memory fake in the tests."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from reports.domain.releases import Release
from reports.domain.reports import Report


class SourceRefused(Exception):
    """The site refused a request, or answered with something other than what was asked. Never worked around."""


class ReadingFailed(Exception):
    """A PDF couldn't be read: MinerU is unavailable, or failed on it. The PDF is kept and read again later."""


@dataclass(frozen=True)
class ReadText:
    """A report's text as metamorph-pdf-text wrote it: page by page, with "<!-- page N -->" markers."""

    text: str
    pages: int
    method: str  # text_layer, or ocr when any page kept was read by OCR
    engine: str
    engine_version: str
    tier: str
    ocr_mode: str
    pages_ocrd: int
    pages_fallen_back: int


class Reader(Protocol):
    def read(self, pdf: bytes) -> ReadText:
        """Raises ReadingFailed when the PDF can't be read now."""
        ...


@dataclass(frozen=True)
class Reading:
    """How a kept report was read: its text is kept as a file, by sha256."""

    text: str  # the text's sha256
    pages: int
    method: str
    engine: str
    engine_version: str
    tier: str
    ocr_mode: str
    pages_ocrd: int
    pages_fallen_back: int


@dataclass(frozen=True)
class KeptReport:
    report: Report
    pdf: str  # the PDF's sha256
    page_url: str | None  # the page that lists it
    file_url: str | None  # the PDF as published
    fetched_at: str  # ISO datetime
    reading: Reading | None  # None until it has been read
    note: str = ""  # why it isn't read yet


class Store(Protocol):
    def keep_file(self, data: bytes) -> str:
        """Keeps the bytes as they are; returns their sha256."""
        ...

    def file(self, sha: str) -> bytes: ...

    def keep_report(self, kept: KeptReport) -> None:
        """Replaces a report kept before under the same ID."""
        ...

    def report(self, report_id: str) -> KeptReport | None: ...

    def reports(self) -> list[KeptReport]:
        """By ID."""
        ...

    def synced(self, at: str) -> None:
        """Records a sync of OJK's listing that went through."""
        ...

    def last_synced(self) -> str | None: ...

    def keep_release(self, kept: KeptRelease) -> None: ...

    def release(self, release_id: str) -> KeptRelease | None: ...

    def releases(self) -> list[KeptRelease]:
        """Newest first."""
        ...

    def walked_back_to(self, since: str) -> None:
        """Records that the release listing was walked whole back to this ISO date."""
        ...

    def walked_back(self) -> str | None:
        """The earliest date the release listing was walked whole back to; None until a walk reached its end."""
        ...


@dataclass(frozen=True)
class ReportPage:
    title: str  # as the page states it
    pdfs: tuple[str, ...]  # the PDFs the page links, as absolute URLs


class LpksiListing(Protocol):
    def editions(self) -> list[str]:
        """Every edition page OJK's LPKSI listing links, as absolute URLs."""
        ...

    def page(self, url: str) -> ReportPage: ...

    def download(self, url: str) -> bytes:
        """The PDF as published; raises SourceRefused when the answer isn't a PDF."""
        ...


@dataclass(frozen=True)
class Listed:
    """A release as the listing shows it."""

    url: str  # its page, absolute
    title: str  # as listed
    listed: str  # its date as listed, e.g. "8 Oktober 2026"


@dataclass(frozen=True)
class ReleasePage:
    body: str  # the release as its page publishes it (HTML); "" when the page holds none
    text: str  # its words, paragraphs separated by blank lines
    pdf: str | None  # the release as a PDF, when the page links one


class ReleaseListing(Protocol):
    def pages(self) -> Iterator[list[Listed]]:
        """The listing's pages, newest first, through its own pager. Raises SourceRefused when a page is refused
        or the pager doesn't move forward."""
        ...

    def release(self, url: str) -> ReleasePage: ...


@dataclass(frozen=True)
class KeptRelease:
    release: Release
    body: str  # the body's sha256
    text: str  # its words
    page_url: str
    pdf_url: str | None
    fetched_at: str  # ISO datetime


class BundleExporter(Protocol):
    def export(
        self,
        reports: Sequence[KeptReport],
        releases: Sequence[KeptRelease],
        files: Mapping[str, bytes],
        out: Path,
        run_id: str,
    ) -> int:
        """Writes one bundle of every read report and every release; returns the number of records."""
        ...
