"""OJK's press releases on ojk.go.id: a listing of ten a page, newest first, and one page per release.

Older listing pages come through the pager's own postback: the page's form, with the page's state, posted back
naming the pager link, as the page's scripts do when a person clicks it. Only the links the pages show are followed.
"""

from __future__ import annotations

import html
import re
from collections.abc import Iterator
from urllib.parse import urljoin

from reports.adapters.web import release_html
from reports.adapters.web.ojk_site import OjkSite
from reports.application.ports import Listed, ReleasePage, SourceRefused

LISTING = "https://ojk.go.id/id/berita-dan-kegiatan/siaran-pers/Default.aspx"
ITEM = re.compile(  # a release as listed: its date, its page, its title
    r'<div class="date">\s*([^<]+?)\s*</div>\s*'
    r'<a href="([^"]*/siaran-pers/Pages/[^"]+)"[^>]*>\s*<strong>(.*?)</strong>',
    re.S,
)
PAGER = re.compile(r'class="pagination">(.*?)</span>\s*</nav>', re.S)
PAGER_LINK = re.compile(r'currentPagingButton">(\d+)<|__doPostBack\(&#39;([^&]+)&#39;,&#39;&#39;\)">([^<]+)</a>')
HIDDEN_INPUT = re.compile(r'<input[^>]*type="hidden"[^>]*>')
NAME, VALUE = re.compile(r'name="([^"]+)"'), re.compile(r'value="([^"]*)"')


class OjkReleases:
    def __init__(self, site: OjkSite) -> None:
        self.site = site

    def pages(self) -> Iterator[list[Listed]]:
        page = self.site.get(LISTING).text
        while True:
            yield _listed(page)
            target = next_page(page)
            if target is None:
                return
            following = self.site.post(LISTING, {**_form(page), "__EVENTTARGET": target, "__EVENTARGUMENT": ""}).text
            if _current(following) <= _current(page):
                raise SourceRefused(f"{LISTING}: the pager answered page {_current(following)} after page "
                                    f"{_current(page)}")
            page = following

    def release(self, url: str) -> ReleasePage:
        page = self.site.get(url).text
        body = release_html.body(page)
        return ReleasePage(body, release_html.text(body), release_html.pdf(page, url))


def next_page(page: str) -> str | None:
    """The pager link right after the current page: the next page's, or the next block's ("…"); None at the end."""
    pager = PAGER.search(page)
    links = PAGER_LINK.findall(pager[1]) if pager else []
    after = [(target, label) for current, target, label in links[_index_of_current(links) + 1 :] if not current]
    return next((target for target, label in after[:1] if label.isdigit() or label == "..."), None)


def _index_of_current(links: list[tuple[str, str, str]]) -> int:
    return next((index for index, (current, _, _) in enumerate(links) if current), len(links))


def _current(page: str) -> int:
    found = re.search(r'currentPagingButton">(\d+)<', page)
    return int(found[1]) if found else 0


def _listed(page: str) -> list[Listed]:
    return [Listed(urljoin(LISTING, html.unescape(href)), " ".join(html.unescape(title).split()), date)
            for date, href, title in ITEM.findall(page)]


def _form(page: str) -> dict[str, str]:
    """The page's hidden fields, as its form would post them."""
    form = {}
    for field in HIDDEN_INPUT.findall(page):
        name, value = NAME.search(field), VALUE.search(field)
        if name:
            form[html.unescape(name[1])] = html.unescape(value[1]) if value else ""
    return form
