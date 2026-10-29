"""Settings come from the environment, so nothing machine-specific lives in the repository."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from reports import __version__

DATA_SETTING = "REPORTS_DATA"  # where the connector keeps reports; default data/
CONTACT_SETTING = "REPORTS_CONTACT"  # optional, e.g. mailto:team@example.com: added to the User-Agent
MINERU_URL_SETTING = "METAMORPH_MINERU_URL"  # the MinerU service: reading a report needs it
MINERU_API_KEY_SETTING = "METAMORPH_MINERU_API_KEY"
RELEASES_SINCE_SETTING = "RELEASES_SINCE"  # the oldest press release kept (YYYY-MM-DD)
RELEASES_SINCE = date(2020, 1, 1)  # set by the project owner on 2026-10-28


@dataclass(frozen=True)
class Config:
    data: Path
    mineru_url: str | None = None
    mineru_api_key: str | None = None
    contact: str | None = None
    releases_since: date = RELEASES_SINCE

    @property
    def mineru_cache(self) -> Path:
        """Every MinerU reading, kept: a report is never sent to MinerU twice alike."""
        return self.data / "mineru-cache"

    @property
    def user_agent(self) -> str:
        """Names the connector to OJK's site, as the other connectors name themselves."""
        return f"reports/{__version__}" + (f" (+{self.contact})" if self.contact else "")

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] = os.environ) -> Config:
        return cls(
            data=Path(environment.get(DATA_SETTING) or "data"),
            mineru_url=environment.get(MINERU_URL_SETTING) or None,
            mineru_api_key=environment.get(MINERU_API_KEY_SETTING) or None,
            contact=environment.get(CONTACT_SETTING) or None,
            releases_since=date.fromisoformat(environment.get(RELEASES_SINCE_SETTING) or RELEASES_SINCE.isoformat()),
        )
