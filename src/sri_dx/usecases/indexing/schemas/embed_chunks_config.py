"""Schemas para configuración de EmbedChunksUseCase."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class EmbedChunksConfig(BaseModel):
    """Configuración para EmbedChunksUseCase.

    Campos equivalentes a la antigua dataclass, ahora como Pydantic model.
    """

    model_config = ConfigDict(title="EmbedChunksConfig")

    chunks_host: str = "localhost"
    chunks_port: int = 9200
    chunks_index: str = "clinical_chunks_v1"

    embeddings_host: str = "localhost"
    embeddings_port: int = 9200
    embeddings_index: str = "clinical_embeddings_v1"
    embeddings_alias: str = "clinical_embeddings"

    batch_size: int = 32
    skip_existing: bool = True

    seed_group: Optional[str] = None
    source_domain: Optional[str] = None
