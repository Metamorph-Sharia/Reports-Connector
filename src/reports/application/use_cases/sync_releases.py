"""Sync OJK's press releases: every release listed since a date, each kept once, newest first.

The listing is walked a page at a time. Releases before the date end the walk, and so does the listing's end; either
way the history is then whole back to the date. Once it is, a sync stops at the first page with nothing new. Until
it is (the first walk, or one a refusal stopped), kept releases cost only their listing page, and the walk goes on
to where it stopped. A refusal stops the sync, which then isn't recorded as one that went through.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import unquote

from reports.application.ports import KeptRelease, Listed, ReleaseListing, Store
from reports.domain.releases import Release, listed_date, number, release_id

ISSUER = "ojk"


@dataclass(frozen=True)
class SyncedRelease:
    url: str  # the release's page
    release_id: str | None
    note: str  # kept, or why not
    kept: KeptRelease | None = None


class SyncReleases:
    def __init__(self, listing: ReleaseListing, store: Store, since: date, now: Callable[[], datetime]) -> None:
        self.listing = listing
        self.store = store
        self.since = since
        self.now = now

    def __call__(self) -> Iterator[SyncedRelease]:
        whole = (self.store.walked_back() or date.max.isoformat()) <= self.since.isoformat()
        reached = True  # unless a page stops the walk first
        for page in self.listing.pages():
            dated = [(listed, _day(listed)) for listed in page]
            yield from (SyncedRelease(listed.url, None, day) for listed, day in dated if isinstance(day, str))
            dated = [(listed, day) for listed, day in dated if isinstance(day, date)]
            synced = [self._release(listed, day) for listed, day in dated if day >= self.since]
            synced = [outcome for outcome in synced if outcome is not None]
            yield from synced
            if any(day < self.since for _, day in dated):
                break
            if whole and not synced:
                reached = False
                break
        if reached:
            self.store.walked_back_to(self.since.isoformat())
        self.store.synced(self.now().isoformat(timespec="seconds"))

    def _release(self, listed: Listed, day: date) -> SyncedRelease | None:
        """None for a release kept already."""
        page_name = unquote(listed.url.rsplit("/", 1)[-1])
        key = release_id(ISSUER, day, page_name)
        kept = self.store.release(key)
        if kept is not None:
            return None if kept.page_url == listed.url else SyncedRelease(
                listed.url, key, f"its ID is taken by {kept.page_url}: not kept")
        page = self.listing.release(listed.url)
        if not page.body:
            return SyncedRelease(listed.url, key, "no release on its page")
        release = Release(key, ISSUER, number(page.text), listed.title, day.isoformat())
        kept = KeptRelease(release, self.store.keep_file(page.body.encode()), page.text, listed.url, page.pdf,
                           self.now().isoformat(timespec="seconds"))
        self.store.keep_release(kept)
        return SyncedRelease(listed.url, key, "kept", kept)


def _day(listed: Listed) -> date | str:
    """The listed date, or why it can't be read."""
    try:
        return listed_date(listed.listed)
    except ValueError as error:
        return str(error)
