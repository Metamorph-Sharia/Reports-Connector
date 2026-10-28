"""In-memory stand-ins for the ports, so use cases are tested without the network, MinerU or files."""

from __future__ import annotations

import hashlib
from dataclasses import replace

from reports.application.ports import KeptReport, ReadingFailed, ReadText, ReportPage, SourceRefused

NOW = "2026-10-28T09:00:00+00:00"
BASE = "https://ojk.go.id/id/kanal/syariah/data-dan-statistik/laporan-perkembangan-keuangan-syariah-indonesia"


def pdf_of(year: str) -> bytes:
    return f"%PDF-1.7 LPKSI {year}".encode()


def edition_page(year: str) -> str:
    return f"{BASE}/Pages/Laporan-Perkembangan-Keuangan-Syariah-Indonesia-{year}.aspx"


def pdf_url(year: str) -> str:
    return f"{BASE}/Documents/LPKSI%20{year}.pdf"


class FakeListing:
    """LPKSI editions by year; `refuse` makes one URL's request refused."""

    def __init__(self, years: list[str], refuse: str | None = None, pages: dict[str, ReportPage] | None = None) -> None:
        self.years = years
        self.refuse = refuse
        self.pages = pages or {}
        self.asked: list[str] = []

    def editions(self) -> list[str]:
        return [edition_page(year) for year in self.years]

    def page(self, url: str) -> ReportPage:
        self._ask(url)
        if url in self.pages:
            return self.pages[url]
        year = url.rsplit("-", 1)[-1].removesuffix(".aspx")
        return ReportPage(f"Laporan Perkembangan Keuangan Syariah Indonesia {year}", (pdf_url(year),))

    def download(self, url: str) -> bytes:
        self._ask(url)
        return pdf_of(url.rsplit("%20", 1)[-1].removesuffix(".pdf"))

    def _ask(self, url: str) -> None:
        self.asked.append(url)
        if url == self.refuse:
            raise SourceRefused(f"{url}: HTTP 403")


class FakeReader:
    """Reads any PDF into two pages of text naming it; `unavailable` makes every read fail, as without MinerU."""

    def __init__(self, unavailable: bool = False) -> None:
        self.unavailable = unavailable
        self.read_count = 0

    def read(self, pdf: bytes) -> ReadText:
        if self.unavailable:
            raise ReadingFailed("MinerU is unavailable: METAMORPH_MINERU_URL is not set")
        self.read_count += 1
        name = pdf.decode().removeprefix("%PDF-1.7 ")
        return ReadText(f"<!-- page 1 -->\n{name}\n\n<!-- page 2 -->\nKeuangan syariah.", 2, "text_layer",
                        "mineru", "4.0.12", "basic", "auto", 0, 0)


class MemoryStore:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.kept: dict[str, KeptReport] = {}
        self.syncs: list[str] = []

    def keep_file(self, data: bytes) -> str:
        sha = hashlib.sha256(data).hexdigest()
        self.files[sha] = data
        return sha

    def file(self, sha: str) -> bytes:
        return self.files[sha]

    def keep_report(self, kept: KeptReport) -> None:
        self.kept[kept.report.id] = kept

    def report(self, report_id: str) -> KeptReport | None:
        return self.kept.get(report_id)

    def reports(self) -> list[KeptReport]:
        return [self.kept[key] for key in sorted(self.kept)]

    def synced(self, at: str) -> None:
        self.syncs.append(at)

    def last_synced(self) -> str | None:
        return self.syncs[-1] if self.syncs else None

    def unread(self, report_id: str) -> None:
        self.kept[report_id] = replace(self.kept[report_id], reading=None, note="MinerU is unavailable")
