from __future__ import annotations

from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from sri_dx.modules.acquisition.ports import RobotsPolicy


class RobotsTxtPolicy(RobotsPolicy):
    """
    Política robots.txt con caché por dominio.
    """

    def __init__(self) -> None:
        self._cache: dict[str, RobotFileParser] = {}

    def allowed(self, url: str, user_agent: str) -> bool:
        p = urlparse(url)
        domain = p.netloc.lower()
        if not domain:
            return True  # URL rara, pero no bloqueamos aquí

        rp = self._cache.get(domain)
        if rp is None:
            rp = RobotFileParser()
            scheme = p.scheme or "https"
            rp.set_url(f"{scheme}://{domain}/robots.txt")
            try:
                rp.read()
            except Exception:
                # Si no se puede leer robots, política práctica para proyecto:
                # permitir para no bloquear el crawler por fallas de red.
                self._cache[domain] = rp
                return True

            self._cache[domain] = rp

        try:
            return rp.can_fetch(user_agent, url)
        except Exception:
            return True