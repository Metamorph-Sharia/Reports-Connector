"""Status: every report kept, read or not, then the releases in one line."""

from __future__ import annotations

from reports.application.ports import Store


class Status:
    def __init__(self, store: Store) -> None:
        self.store = store

    def __call__(self) -> list[str]:
        lines = []
        for kept in self.store.reports():
            reading = kept.reading
            shown = (f"{reading.pages} pages, {reading.method}, fetched {kept.fetched_at[:10]}" if reading
                     else f"unread: {kept.note}")
            lines.append(f"{kept.report.id} {kept.report.title}: {shown}")
        return [*lines, self._releases()]

    def _releases(self) -> str:
        releases = self.store.releases()
        kept = (f"{len(releases)} kept, {releases[-1].release.published_on} to {releases[0].release.published_on}"
                if releases else "none kept")
        return f"releases: {kept}; {walk(self.store.walked_back())}"


def walk(walked_back: str | None) -> str:
    return f"the listing walked whole back to {walked_back}" if walked_back else "the listing not walked whole yet"
