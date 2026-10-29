"""OJK's LPKSI listing over HTTP, replayed from pages saved on 28 Oct 2026."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from reports.adapters.web.ojk_lpksi import LISTING, OjkLpksi
from reports.adapters.web.ojk_site import OjkSite
from reports.application.ports import SourceRefused

FIXTURES = Path(__file__).parent / "fixtures"
PAGES = f"{LISTING.rsplit('/', 1)[0]}/Pages"
PAGE_2025 = f"{PAGES}/Laporan-Perkembangan-Keuangan-Syariah-Indonesia-2025.aspx"
PDF_2025 = ("https://ojk.go.id/id/kanal/syariah/data-dan-statistik/laporan-perkembangan-keuangan-syariah-indonesia/"
            "Documents/Laporan%20Perkembangan%20Keuangan%20Syariah%20Indonesia%20%28LPKSI%29%202025.pdf")
SAVED = {LISTING: "lpksi-listing.html", PAGE_2025: "lpksi-2025.html", f"{PAGES}/2016.aspx": "lpksi-2016.html",
         f"{PAGES}/-%e2%80%8bLaporan-Perkembangan-Keuangan-Syariah-Indonesia-2019.aspx": "lpksi-2019.html"}


class Site:
    def __init__(self, pdf: httpx.Response | None = None) -> None:
        self.pdf = pdf or httpx.Response(200, headers={"Content-Type": "application/pdf"}, content=b"%PDF-1.7 LPKSI")
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        url = str(request.url)
        if url in SAVED:
            return httpx.Response(200, headers={"Content-Type": "text/html; charset=utf-8"},
                                  content=(FIXTURES / SAVED[url]).read_bytes())
        if url.endswith(".pdf"):
            return self.pdf
        return httpx.Response(404)


def listing(site: Site, sleeps: list[float] | None = None) -> OjkLpksi:
    return OjkLpksi(OjkSite(user_agent="reports/0.1.0", transport=httpx.MockTransport(site),
                            sleep=(sleeps if sleeps is not None else []).append, clock=lambda: 0.0))


def test_the_listing_links_ten_edition_pages_from_2016() -> None:
    found = listing(Site()).editions()

    assert len(found) == 10
    assert found[0] == f"{PAGES}/2016.aspx"
    assert found[-1] == PAGE_2025
    assert all(url.startswith(PAGES) for url in found)


def test_an_edition_page_gives_its_title_and_its_one_pdf() -> None:
    page = listing(Site()).page(PAGE_2025)

    assert page.title == "Laporan Perkembangan Keuangan Syariah Indonesia 2025"
    assert page.pdfs == (PDF_2025,)


def test_a_page_title_keeps_what_the_page_says_invisible_characters_included() -> None:
    page = listing(Site()).page(f"{PAGES}/-%e2%80%8bLaporan-Perkembangan-Keuangan-Syariah-Indonesia-2019.aspx")

    assert page.title.endswith("Laporan Perkembangan Keuangan Syariah Indonesia 2019")  # the domain strips the rest
    assert len(page.pdfs) == 1


def test_a_download_is_the_pdf_as_published() -> None:
    assert listing(Site()).download(PDF_2025) == b"%PDF-1.7 LPKSI"


@pytest.mark.parametrize("answer", [
    httpx.Response(403),
    httpx.Response(200, headers={"Content-Type": "text/html"}, content=b"<html>Request Rejected</html>"),
])
def test_a_refusal_or_an_answer_that_is_not_a_pdf_stops(answer: httpx.Response) -> None:
    with pytest.raises(SourceRefused):
        listing(Site(pdf=answer)).download(PDF_2025)


def test_requests_name_the_connector_and_wait_their_turn() -> None:
    site, sleeps = Site(), []
    client = listing(site, sleeps)
    client.editions()
    client.page(PAGE_2025)

    assert {request.headers["User-Agent"] for request in site.requests} == {"reports/0.1.0"}
    assert sleeps == [2.0]
