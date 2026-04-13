from __future__ import annotations

import asyncio
import httpx
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from sri_dx.core.ports.acquisition.robots_policy_port import RobotsPolicyPort


class RobotsTxtPolicy(RobotsPolicyPort):
    """
    Política robots.txt con caché por dominio. Thread-safe.
    """

    def __init__(self, user_agent: str) -> None:
        self.user_agent = user_agent
        self._cache: dict[str, RobotFileParser] = {}
        self._lock = asyncio.Lock()

    async def allowed(self, url: str, user_agent: str) -> bool:
        p = urlparse(url)
        domain = p.netloc.lower()
        if not domain:
            return True

        rp = self._cache.get(domain)
        if rp is not None:
            try:
                return rp.can_fetch(user_agent, url)
            except Exception:
                return True

        # Slow path: fetch robots.txt under lock to avoid duplicate fetches
        async with self._lock:
            # Slow path: fetch robots.txt
            rp = RobotFileParser()
            scheme = p.scheme or "https"
            robots_url = f"{scheme}://{domain}/robots.txt"
            
            try:
                async with httpx.AsyncClient(headers={"User-Agent": self.user_agent}, follow_redirects=True) as client:
                    resp = await client.get(robots_url, timeout=10)
                    if resp.status_code == 404:
                        rp.parse([])
                    elif resp.status_code >= 400:
                        return True
                    else:
                        rp.parse(resp.text.splitlines())
            except Exception:
                self._cache[domain] = rp
                return True
            
            self._cache[domain] = rp

        try:
            return rp.can_fetch(user_agent, url)
        except Exception:
            return True