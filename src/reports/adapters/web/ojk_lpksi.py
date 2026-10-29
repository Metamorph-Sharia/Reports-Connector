"""OJK's LPKSI listing on ojk.go.id: one page per edition, each linking its PDF.

Only the links the pages show are followed, through the connector's one client for the site (ojk_site.py). A
download that isn't the PDF asked for raises SourceRefused: it is reported, never worked around.
"""

from __future__ import annotations

import html
import re
from urllib.parse import urljoin

from reports.adapters.web.ojk_site import OjkSite
from reports.application.ports import ReportPage, SourceRefused

LISTING = "https://ojk.go.id/id/kanal/syariah/data-dan-statistik/laporan-perkembangan-keuangan-syariah-indonesia/Default.aspx"
EDITION_PAGES = "/id/kanal/syariah/data-dan-statistik/laporan-perkembangan-keuangan-syariah-indonesia/Pages/"
CONTENT = "PlaceHolderMain"  # the page's own content starts here, after the site's menus
LINK = re.compile(r'href="([^"]+)"')
TITLE = re.compile(r"<title>(.*?)</title>", re.S)


class OjkLpksi:
    def __init__(self, site: OjkSite) -> None:
        self.site = site

    def editions(self) -> list[str]:
        links = LINK.findall(self.site.get(LISTING).text)
        pages = (html.unescape(href) for href in links if EDITION_PAGES in href and href.endswith(".aspx"))
        return sorted(dict.fromkeys(urljoin(LISTING, page) for page in pages), key=_by_year)

    def page(self, url: str) -> ReportPage:
        body = self.site.get(url).text
        title = TITLE.search(body)
        content = body.split(CONTENT, 1)[-1]
        pdfs = (urljoin(url, html.unescape(href)) for href in LINK.findall(content) if href.lower().endswith(".pdf"))
        return ReportPage(html.unescape(title.group(1)).strip() if title else "", tuple(dict.fromkeys(pdfs)))

    def download(self, url: str) -> bytes:
        response = self.site.get(url)
        if "application/pdf" not in response.headers.get("Content-Type", "") or not response.content.startswith(
            b"%PDF"
        ):
            kind = response.headers.get("Content-Type", "no type")
            raise SourceRefused(f"{url}: answered with {kind}, {len(response.content)} bytes, not the PDF")
        return response.content


def _by_year(url: str) -> str:
    """Oldest first: the year the page's name ends with, so a sync that stops leaves the oldest kept."""
    found = re.findall(r"(\d{4})\.aspx$", url)
    return found[0] if found else url
