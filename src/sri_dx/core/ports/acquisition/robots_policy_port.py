from __future__ import annotations

from typing import Protocol


class RobotsPolicyPort(Protocol):
    """Puerto: política robots.txt. Determina si una URL es rastreable."""

    async def allowed(self, url: str, user_agent: str) -> bool: ...
