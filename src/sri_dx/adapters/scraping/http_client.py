from __future__ import annotations
from datetime import datetime, timezone
import httpx
import certifi

from sri_dx.modules.acquisition.models import FetchResult
from sri_dx.modules.acquisition.ports import HttpClient


class HttpxClient(HttpClient):
    """
    Cliente HTTP real (adapter).
    - Sigue redirects
    - Devuelve FetchResult con mime_type normalizado
    """

    def __init__(self, user_agent: str) -> None:
        self._client = httpx.Client(
            headers={"User-Agent": user_agent},
            follow_redirects=True, verify=False #verify=certifi.where(),
        )

    def get(self, url: str, *, timeout_s: float) -> FetchResult:
        r = self._client.get(url, timeout=timeout_s)
        content_type = (r.headers.get("content-type") or "").split(";")[0].strip().lower()

        return FetchResult(
            url=str(r.url),
            status_code=int(r.status_code),
            mime_type=content_type,
            content=r.content,
            fetched_at=datetime.now(timezone.utc),
            headers={k.lower(): v for k, v in r.headers.items()},
        )