from __future__ import annotations

from typing import Protocol

from sri_dx.core.schemas.acquisition.fetch_result import FetchResult


class HttpClientPort(Protocol):
    """Puerto: cliente HTTP. Realiza GET y retorna el resultado crudo."""

    def get(self, url: str, *, timeout_s: float) -> FetchResult: ...
