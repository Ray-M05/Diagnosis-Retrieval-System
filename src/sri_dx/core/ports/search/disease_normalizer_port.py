from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class DiseaseNormalizerPort(Protocol):
    """Resuelve un nombre de enfermedad a su forma canónica según una ontología externa."""

    def normalize(self, disease_name: str) -> str:
        """Retorna el nombre canónico, o el mismo nombre si no hay match."""
        ...
