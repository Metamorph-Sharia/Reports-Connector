"""OJK's press releases over HTTP, replayed from pages saved on 28 Oct 2026: the listing, its pager, a release."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest

from reports.adapters.web.ojk_releases import LISTING, OjkReleases, next_page
from reports.adapters.web.ojk_site import OjkSite
from reports.application.ports import SourceRefused

FIXTURES = Path(__file__).parent / "fixtures"
PAGES = "https://ojk.go.id/id/berita-dan-kegiatan/siaran-pers/Pages"
PORTO = f"{PAGES}/OJK-Cabut-Izin-Usaha-PT-Porto-Ventura-Kapital.aspx"
TO_PAGE_2 = "ctl00$PlaceHolderMain$ctl01$DataPagerArticles$ctl01$ctl01"
TO_PAGE_3 = "ctl00$PlaceHolderMain$ctl01$DataPagerArticles$ctl01$ctl02"


def html(name: str) -> httpx.Response:
    return httpx.Response(200, headers={"Content-Type": "text/html; charset=utf-8"},
                          content=(FIXTURES / name).read_bytes())


class Site:
    """Answers a postback by the pager link it names, as OJK's site does."""

    def __init__(self, postbacks: dict[str, str] | None = None) -> None:
        saved = {TO_PAGE_2: "releases-listing-2.html", TO_PAGE_3: "releases-listing-161.html"}
        self.postbacks = saved if postbacks is None else postbacks
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        url = str(request.url)
        if request.method == "POST" and url == LISTING:
            target = parse_qs(request.content.decode())["__EVENTTARGET"][0]
            return html(self.postbacks[target]) if target in self.postbacks else httpx.Response(500)
        if url == LISTING:
            return html("releases-listing-1.html")
        if url == PORTO:
            return html("release-porto-ventura.html")
        return httpx.Response(404)


def releases(site: Site, sleeps: list[float] | None = None) -> OjkReleases:
    return OjkReleases(OjkSite(user_agent="reports/0.2.0", transport=httpx.MockTransport(site),
                               sleep=(sleeps if sleeps is not None else []).append, clock=lambda: 0.0))


def test_the_first_page_lists_ten_releases_newest_first() -> None:
    first = next(releases(Site()).pages())

    assert len(first) == 10
    assert first[0].listed == "27 Oktober 2026"
    assert first[0].url == f"{PAGES}/The-4th-OJK-International-Research-Forum-2026.aspx"
    assert first[0].title.startswith("Siaran Pers: OJK Perkuat Kebijakan Berbasis Riset")
    assert first[-1].listed == "20 Oktober 2026"


def test_older_pages_come_through_the_pagers_own_postback() -> None:
    site = Site()
    pages = releases(site).pages()
    first, second, third = next(pages), next(pages), next(pages)

    assert second[0].listed == "18 Oktober 2026"
    assert third[0].listed == "15 Juli 2014"  # page 161, as the saved answer to the third postback
    post = parse_qs(site.requests[1].content.decode())
    assert post["__EVENTTARGET"] == [TO_PAGE_2]
    assert len(post["__VIEWSTATE"][0]) > 100_000  # the page's own state, posted back as a browser would
    assert {first[0].url, second[0].url}.isdisjoint({release.url for release in third})


def test_a_pager_that_does_not_move_forward_stops_the_listing() -> None:
    pages = releases(Site({TO_PAGE_2: "releases-listing-1.html"})).pages()
    next(pages)

    with pytest.raises(SourceRefused, match="the pager answered page 1 after page 1"):
        next(pages)


def test_a_refused_postback_stops_the_listing() -> None:
    pages = releases(Site({})).pages()
    next(pages)

    with pytest.raises(SourceRefused, match="HTTP 500"):
        next(pages)


@pytest.mark.parametrize(("pager", "target"), [
    ('<span class="currentPagingButton">1</span>&nbsp;<a class="pagingButton" '
     'href="javascript:__doPostBack(&#39;to2&#39;,&#39;&#39;)">2</a>', "to2"),
    ('<a class="pagingButton" href="javascript:__doPostBack(&#39;back&#39;,&#39;&#39;)">...</a>'
     '<span class="currentPagingButton">10</span>&nbsp;<a class="pagingButton" '
     'href="javascript:__doPostBack(&#39;to11&#39;,&#39;&#39;)">...</a>', "to11"),
    ('<a class="pagingButton" href="javascript:__doPostBack(&#39;back&#39;,&#39;&#39;)">...</a>'
     '<span class="currentPagingButton">165</span>&nbsp;<a class="pagingButton fa fa-arrow-right"></a>', None),
])
def test_the_next_page_is_the_link_right_after_the_current_one(pager: str, target: str | None) -> None:
    page = f'<span id="x_DataPagerArticles" class="pagination">{pager}&nbsp;</span> </nav>'

    assert next_page(page) == target


def test_a_release_page_gives_its_body_its_words_and_its_pdf() -> None:
    page = releases(Site()).release(PORTO)

    assert page.body.startswith('<div id="summary">')
    assert page.text.startswith("SP 188/DKPU/OJK/X/2026\n\nSIARAN PERS")
    assert page.pdf.endswith("/OJK-Cabut-Izin-Usaha-PT-Porto-Ventura-Kapital/SP%20188%20OJK%20Cabut%20Izin%20Usaha"
                             "%20PT%20Porto%20Ventura%20Kapital.pdf")


def test_requests_name_the_connector_and_wait_their_turn() -> None:
    site, sleeps = Site(), []
    client = releases(site, sleeps)
    pages = client.pages()
    next(pages), next(pages)
    client.release(PORTO)

    assert {request.headers["User-Agent"] for request in site.requests} == {"reports/0.2.0"}
    assert sleeps == [2.0, 2.0]
