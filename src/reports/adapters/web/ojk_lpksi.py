"""OJK's LPKSI listing on ojk.go.id: one page per edition, each linking its PDF.

Only the links the pages show are followed. Every request names the connector in its User-Agent and waits its
turn, one every two seconds. A refusal, or an answer other than the one asked for, raises SourceRefused: it is
reported, never worked around.
"""

from __future__ import annotations

import html
import re
import time
from collections.abc import Callable
from urllib.parse import urljoin

import httpx

from reports.application.ports import ReportPage, SourceRefused

LISTING = "https://ojk.go.id/id/kanal/syariah/data-dan-statistik/laporan-perkembangan-keuangan-syariah-indonesia/Default.aspx"
EDITION_PAGES = "/id/kanal/syariah/data-dan-statistik/laporan-perkembangan-keuangan-syariah-indonesia/Pages/"
REQUEST_INTERVAL = 2.0  # seconds between requests
CONTENT = "PlaceHolderMain"  # the page's own content starts here, after the site's menus
LINK = re.compile(r'href="([^"]+)"')
TITLE = re.compile(r"<title>(.*?)</title>", re.S)
TIMEOUT = httpx.Timeout(60.0, read=180.0)  # a report's PDF runs to 135 MB


class OjkLpksi:
    def __init__(
        self,
        *,
        user_agent: str,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._http = httpx.Client(transport=transport, timeout=TIMEOUT, headers={"User-Agent": user_agent})
        self._sleep = sleep
        self._clock = clock
        self._last_request: float | None = None

    def editions(self) -> list[str]:
        links = LINK.findall(self._get(LISTING).text)
        pages = (html.unescape(href) for href in links if EDITION_PAGES in href and href.endswith(".aspx"))
        return sorted(dict.fromkeys(urljoin(LISTING, page) for page in pages), key=_by_year)

    def page(self, url: str) -> ReportPage:
        body = self._get(url).text
        title = TITLE.search(body)
        content = body.split(CONTENT, 1)[-1]
        pdfs = (urljoin(url, html.unescape(href)) for href in LINK.findall(content) if href.lower().endswith(".pdf"))
        return ReportPage(html.unescape(title.group(1)).strip() if title else "", tuple(dict.fromkeys(pdfs)))

    def download(self, url: str) -> bytes:
        response = self._get(url)
        if "application/pdf" not in response.headers.get("Content-Type", "") or not response.content.startswith(
            b"%PDF"
        ):
            kind = response.headers.get("Content-Type", "no type")
            raise SourceRefused(f"{url}: answered with {kind}, {len(response.content)} bytes, not the PDF")
        return response.content

    def _get(self, url: str) -> httpx.Response:
        self._wait_turn()
        try:
            response = self._http.get(url)
        except httpx.TransportError as error:
            raise SourceRefused(f"{url}: {error}") from error
        if response.status_code != 200:
            raise SourceRefused(f"{url}: HTTP {response.status_code}")
        return response

    def _wait_turn(self) -> None:
        if self._last_request is not None:
            wait = REQUEST_INTERVAL - (self._clock() - self._last_request)
            if wait > 0:
                self._sleep(wait)
        self._last_request = self._clock()


def _by_year(url: str) -> str:
    """Oldest first: the year the page's name ends with, so a sync that stops leaves the oldest kept."""
    found = re.findall(r"(\d{4})\.aspx$", url)
    return found[0] if found else url
