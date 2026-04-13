from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CrawlTask:
    """Unidad de trabajo del crawler."""
    url: str
    depth: int
    parent_url: Optional[str]
    seed_id: str
    seed_group: str