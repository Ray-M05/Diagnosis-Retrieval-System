from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FetchResult:
    """Raw result of an HTTP request (server response)."""
    url: str
    status_code: int
    mime_type: str
    content: bytes
    fetched_at: datetime
    headers: dict[str, str]
