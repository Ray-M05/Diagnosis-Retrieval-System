# src/sri_dx/modules/indexing/index_upsert.py
from __future__ import annotations
from dataclasses import dataclass
from sri_dx.core.schemas.indexing.index_document import IndexDocument

@dataclass(frozen=True)
class IndexUpsert:
    doc: IndexDocument
    concept_ids: list[str]
