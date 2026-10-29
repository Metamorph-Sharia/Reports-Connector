"""A release's page on ojk.go.id: its body as published (<div id="summary">), and the words in it.

One general rule turns the body's HTML into text, never a rule per release:
- block elements (p, div, headings, tables, lists) end a paragraph, and paragraphs are separated by a blank line;
- a line break, a table row and a list item end a line, so a table or a list stays one paragraph;
- a row's cells are joined by " | ";
- within a list item a block ends a line, and within a cell it is a space, so an item or a cell stays whole;
- what the page hides (style display:none) and images are not words of the release.
"""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from urllib.parse import urljoin

BODY = "summary"  # the id of the element holding the release
PARAGRAPH_TAGS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "table", "ul", "ol", "blockquote"}
LINE_TAGS = {"br", "tr", "li"}
CELL_TAGS = {"td", "th"}
SKIPPED_TAGS = {"script", "style"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
HIDDEN = re.compile(r"display\s*:\s*none", re.I)
SPACES = re.compile(r"[ \t\r\f\v ]+")
INVISIBLE = re.compile("[\\u200b-\\u200f\\u2060\\ufeff]")
PARAGRAPH, LINE = "\x02", "\x01"  # breaks, as markers no page contains
PDF_LINK = re.compile(r'href="([^"]+/siaran-pers/Documents/[^"]+\.pdf)"', re.I)


def body(page: str) -> str:
    """The element holding the release, as the page published it; "" when the page has none."""
    start = page.find(f'<div id="{BODY}">')
    if start < 0:
        return ""
    finder = _End()
    finder.feed(page[start:])
    return page[start : start + finder.end] if finder.end else page[start:]


def text(body_html: str) -> str:
    words = _Words()
    words.feed(body_html)
    words.close()
    return words.text()


def pdf(page: str, url: str) -> str | None:
    """The release as a PDF, when the page links one."""
    found = PDF_LINK.search(page)
    return urljoin(url, html.unescape(found[1])) if found else None


class _End(HTMLParser):
    """Where the first element closes, counted in characters of what was fed."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.open: list[str] = []
        self.end = 0
        self.fed = ""

    def feed(self, data: str) -> None:
        self.fed = data
        super().feed(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in VOID_TAGS and not self.end:
            self.open.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if self.end or tag not in self.open:
            return
        while self.open.pop() != tag:
            pass
        if not self.open:
            line, column = self.getpos()
            offset = sum(len(text) for text in self.fed.splitlines(keepends=True)[: line - 1]) + column
            self.end = self.fed.index(">", offset) + 1


class _Words(HTMLParser):
    """Words and breaks; a break is a marker until the end, so breaks that meet don't add up."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.open: list[tuple[str, bool]] = []  # each open element, and whether it hides what it holds
        self.cells = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        hides = tag in SKIPPED_TAGS or bool(HIDDEN.search(dict(attrs).get("style") or ""))
        if tag not in VOID_TAGS:
            self.open.append((tag, hides))
        if self._hidden():
            return
        if tag in PARAGRAPH_TAGS:
            self.out.append(self._block_break())
        elif tag in LINE_TAGS:
            self.out.append(LINE)
            self.cells = 0
        elif tag in CELL_TAGS:
            self.out.append(" | " if self.cells else "")
            self.cells += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID_TAGS or tag not in {name for name, _ in self.open}:
            return
        while self.open.pop()[0] != tag:
            pass
        if self._hidden():
            return
        if tag in PARAGRAPH_TAGS:
            self.out.append(self._block_break())
        elif tag in LINE_TAGS:
            self.out.append(LINE)

    def handle_data(self, data: str) -> None:
        if not self._hidden():
            self.out.append(" ".join(data.splitlines()))  # the source's own line ends are spaces

    def _block_break(self) -> str:
        """A block's break: a paragraph's, or within a list item a line's, or within a cell a space."""
        container = next((name for name, _ in reversed(self.open) if name in CELL_TAGS | {"li"}), None)
        return {"li": LINE, None: PARAGRAPH}.get(container, " ")

    def _hidden(self) -> bool:
        return any(hides for _, hides in self.open)

    def text(self) -> str:
        paragraphs = []
        for block in "".join(self.out).split(PARAGRAPH):
            lines = (SPACES.sub(" ", INVISIBLE.sub("", line)).strip(" |") for line in block.split(LINE))
            if kept := [line.strip() for line in lines if line.strip()]:
                paragraphs.append("\n".join(kept))
        return "\n\n".join(paragraphs)
