from __future__ import annotations
from datetime import datetime, timezone
import asyncio
import httpx
import certifi

from sri_dx.core.schemas.acquisition.fetch_result import FetchResult
from sri_dx.core.ports.acquisition.http_client_port import HttpClientPort


class HttpxClient(HttpClientPort):
    """
    Cliente HTTP real (adapter).
    - Sigue redirects
    - Devuelve FetchResult con mime_type normalizado
    """

    def __init__(self, user_agent: str, verify_ssl: bool = True) -> None:
        self._client = httpx.AsyncClient(
            headers={"User-Agent": user_agent},
            follow_redirects=True, verify=(certifi.where() if verify_ssl else False),
        )

    async def get(self, url: str, *, timeout_s: float) -> FetchResult:
        max_retries = 3
        backoff_factor = 2

        last_exc: Exception | None = None
        
        for attempt in range(max_retries):
            try:
                r = await self._client.get(url, timeout=timeout_s)
                
                # Success or non-retryable error
                if r.status_code < 400 or r.status_code in (404, 401, 403):
                    break
                
                # Retryable errors
                if r.status_code == 429 or r.status_code >= 500:
                    wait_time = backoff_factor ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                
                # Other 4xx errors
                break

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exc = e
                wait_time = backoff_factor ** attempt
                await asyncio.sleep(wait_time)
                continue
            except Exception as e:
                # Unexpected error, don't retry
                raise e
        else:
            # If we exhausted retries and have an exception, re-raise it
            if last_exc:
                raise last_exc

        content_type = (r.headers.get("content-type") or "").split(";")[0].strip().lower()

        return FetchResult(
            url=str(r.url),
            status_code=int(r.status_code),
            mime_type=content_type,
            content=r.content,
            fetched_at=datetime.now(timezone.utc),
            headers={k.lower(): v for k, v in r.headers.items()},
        )