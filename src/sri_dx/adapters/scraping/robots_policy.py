from __future__ import annotations

import threading
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from sri_dx.modules.acquisition.ports import RobotsPolicy


class RobotsTxtPolicy(RobotsPolicy):
    """
    Política robots.txt con caché por dominio. Thread-safe.
    """

    def __init__(self) -> None:
        self._cache: dict[str, RobotFileParser] = {}
        self._lock = threading.Lock()

    def allowed(self, url: str, user_agent: str) -> bool:
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
        with self._lock:
            rp = self._cache.get(domain)  # double-check
            if rp is None:
                rp = RobotFileParser()
                scheme = p.scheme or "https"
                rp.set_url(f"{scheme}://{domain}/robots.txt")
                try:
                    rp.read()
                except Exception:
                    self._cache[domain] = rp
                    return True
                self._cache[domain] = rp

        try:
            return rp.can_fetch(user_agent, url)
        except Exception:
            return True