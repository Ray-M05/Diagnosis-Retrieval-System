from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class DiseaseNormalizerPort(Protocol):
    """Resolves a disease name to its canonical form according to an external ontology."""

    def normalize(self, disease_name: str) -> str:
        """Returns the canonical name, or the same name if no match is found."""
        ...
