"""In-memory stand-ins for the ports, so use cases are tested without the network, MinerU or files."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from dataclasses import replace

from reports.application.ports import (
    KeptRelease,
    KeptReport,
    Listed,
    ReadingFailed,
    ReadText,
    ReleasePage,
    ReportPage,
    SourceRefused,
)

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


RELEASES = "https://ojk.go.id/id/berita-dan-kegiatan/siaran-pers/Pages"


def listed(name: str, day: str) -> Listed:
    return Listed(f"{RELEASES}/{name}.aspx", f"Siaran Pers: {name}", day)


class FakeReleases:
    """The release listing as pages of Listed; a release's page names it. `refuse` makes one release refused."""

    def __init__(self, listing: list[list[Listed]], refuse: str | None = None,
                 pages: dict[str, ReleasePage] | None = None) -> None:
        self.listing = listing
        self.refuse = refuse
        self.saved = pages or {}
        self.pages_asked = 0
        self.releases_asked: list[str] = []

    def pages(self) -> Iterator[list[Listed]]:
        for page in self.listing:
            self.pages_asked += 1
            yield page

    def release(self, url: str) -> ReleasePage:
        name = url.rsplit("/", 1)[-1].removesuffix(".aspx")
        self.releases_asked.append(name)
        if name == self.refuse:
            raise SourceRefused(f"{url}: HTTP 403")
        if name in self.saved:
            return self.saved[name]
        return ReleasePage(f'<div id="summary"><p>{name}</p></div>', f"SP 1/DKPU/OJK/X/2026\n\nSIARAN PERS\n\n{name}",
                           f"{RELEASES.replace('Pages', 'Documents')}/{name}.pdf")


class MemoryStore:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.kept: dict[str, KeptReport] = {}
        self.syncs: list[str] = []
        self.kept_releases: dict[str, KeptRelease] = {}
        self.walks: list[str] = []

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

    def keep_release(self, kept: KeptRelease) -> None:
        self.kept_releases[kept.release.id] = kept

    def release(self, release_id: str) -> KeptRelease | None:
        return self.kept_releases.get(release_id)

    def releases(self) -> list[KeptRelease]:
        return sorted(self.kept_releases.values(), key=lambda kept: (kept.release.published_on, kept.release.id),
                      reverse=True)

    def walked_back_to(self, since: str) -> None:
        self.walks.append(since)

    def walked_back(self) -> str | None:
        return min(self.walks) if self.walks else None

    def unread(self, report_id: str) -> None:
        self.kept[report_id] = replace(self.kept[report_id], reading=None, note="MinerU is unavailable")
