"""ojk.go.id over HTTP, shared by everything the connector reads there.

Every request names the connector in its User-Agent and waits its turn, one every two seconds, across all of the
connector's requests to the site. A refusal, or an answer other than 200, raises SourceRefused: it is reported,
never worked around.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping

import httpx

from reports.application.ports import SourceRefused

REQUEST_INTERVAL = 2.0  # seconds between requests
TIMEOUT = httpx.Timeout(60.0, read=180.0)  # a report's PDF runs to 135 MB


class OjkSite:
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

    def get(self, url: str) -> httpx.Response:
        return self._ask("GET", url)

    def post(self, url: str, form: Mapping[str, str]) -> httpx.Response:
        """A form posted back to its page, as the page's own scripts post it."""
        return self._ask("POST", url, data=dict(form))

    def _ask(self, method: str, url: str, **content: object) -> httpx.Response:
        self._wait_turn()
        try:
            response = self._http.request(method, url, **content)
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
