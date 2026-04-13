from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ManifestEntry:
    doc_id: str
    content_hash: str
    pipeline_version: str


class ManifestStorePort(ABC):
    @abstractmethod
    def get(self, doc_id: str) -> ManifestEntry | None:
        raise NotImplementedError

    @abstractmethod
    def get_many(self, doc_ids: Iterable[str]) -> dict[str, ManifestEntry]:
        raise NotImplementedError

    @abstractmethod
    def upsert_many(self, entries: Iterable[ManifestEntry]) -> None:
        raise NotImplementedError
