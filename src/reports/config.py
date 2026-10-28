"""Settings come from the environment, so nothing machine-specific lives in the repository."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from reports import __version__

DATA_SETTING = "REPORTS_DATA"  # where the connector keeps reports; default data/
CONTACT_SETTING = "REPORTS_CONTACT"  # optional, e.g. mailto:team@example.com: added to the User-Agent
MINERU_URL_SETTING = "METAMORPH_MINERU_URL"  # the MinerU service: reading a report needs it
MINERU_API_KEY_SETTING = "METAMORPH_MINERU_API_KEY"


@dataclass(frozen=True)
class Config:
    data: Path
    mineru_url: str | None = None
    mineru_api_key: str | None = None
    contact: str | None = None

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
        )
