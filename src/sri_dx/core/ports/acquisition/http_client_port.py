from __future__ import annotations

from typing import Protocol

from sri_dx.core.schemas.acquisition.fetch_result import FetchResult


class HttpClientPort(Protocol):
    """HTTP client port. Performs GET requests and returns raw results."""

    async def get(self, url: str, *, timeout_s: float) -> FetchResult: ...
