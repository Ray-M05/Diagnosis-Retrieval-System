"""Centralised OpenSearch index/alias naming for SRI-DX.

The system keeps **separate corpora** so that web-enriched content never
pollutes the local corpus:

- Local docs/chunks live in ``*_local_*`` indices (the default retrieval target).
- Web-enriched docs/chunks live in ``*_web_*`` indices, queried only when the
  sufficiency indicator triggers and web search is active.
- A **single, shared** embeddings/vector index holds every chunk vector; each
  embedding stores ``chunk_id``/``doc_id``/``seed_group`` in its metadata, so the
  local/web origin is recoverable by filter without a federated kNN query.

This module is the single source of truth for those names. Sinks and readers
should build their per-store configs from an :class:`IndexNames` instance rather
than hard-coding literals or re-reading the environment.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping, Optional

if TYPE_CHECKING:  # avoid import cycle at runtime
    from sri_dx.core.config import SRIConfig


# Defaults — local names intentionally match the historical ``clinical_*_v1``
# scheme so nothing breaks before the corpora are split.
_DEFAULTS: dict[str, str] = {
    "docs_local_index": "clinical_docs_local_v1",
    "docs_local_alias": "clinical_docs_local",
    "docs_web_index": "clinical_docs_web_v1",
    "docs_web_alias": "clinical_docs_web",
    "chunks_local_index": "clinical_chunks_local_v1",
    "chunks_local_alias": "clinical_chunks_local",
    "chunks_web_index": "clinical_chunks_web_v1",
    "chunks_web_alias": "clinical_chunks_web",
    "embeddings_index": "clinical_embeddings_v1",
    "embeddings_alias": "clinical_embeddings",
}

# env var -> field mapping
_ENV_MAP: dict[str, str] = {
    "docs_local_index": "SRI_DOCS_LOCAL_INDEX",
    "docs_local_alias": "SRI_DOCS_LOCAL_ALIAS",
    "docs_web_index": "SRI_DOCS_WEB_INDEX",
    "docs_web_alias": "SRI_DOCS_WEB_ALIAS",
    "chunks_local_index": "SRI_CHUNKS_LOCAL_INDEX",
    "chunks_local_alias": "SRI_CHUNKS_LOCAL_ALIAS",
    "chunks_web_index": "SRI_CHUNKS_WEB_INDEX",
    "chunks_web_alias": "SRI_CHUNKS_WEB_ALIAS",
    "embeddings_index": "SRI_EMBEDDINGS_INDEX",
    "embeddings_alias": "SRI_EMBEDDINGS_ALIAS",
}


@dataclass(frozen=True)
class IndexNames:
    """Resolved names for every OpenSearch index/alias used by the system."""

    docs_local_index: str = _DEFAULTS["docs_local_index"]
    docs_local_alias: str = _DEFAULTS["docs_local_alias"]
    docs_web_index: str = _DEFAULTS["docs_web_index"]
    docs_web_alias: str = _DEFAULTS["docs_web_alias"]
    chunks_local_index: str = _DEFAULTS["chunks_local_index"]
    chunks_local_alias: str = _DEFAULTS["chunks_local_alias"]
    chunks_web_index: str = _DEFAULTS["chunks_web_index"]
    chunks_web_alias: str = _DEFAULTS["chunks_web_alias"]
    embeddings_index: str = _DEFAULTS["embeddings_index"]
    embeddings_alias: str = _DEFAULTS["embeddings_alias"]

    def docs_index(self, *, web: bool) -> str:
        return self.docs_web_index if web else self.docs_local_index

    def docs_alias(self, *, web: bool) -> str:
        return self.docs_web_alias if web else self.docs_local_alias

    def chunks_index(self, *, web: bool) -> str:
        return self.chunks_web_index if web else self.chunks_local_index

    def chunks_alias(self, *, web: bool) -> str:
        return self.chunks_web_alias if web else self.chunks_local_alias

    def all_indices(self) -> list[str]:
        return [
            self.docs_local_index,
            self.docs_web_index,
            self.chunks_local_index,
            self.chunks_web_index,
            self.embeddings_index,
        ]


def resolve_index_names(
    cfg: Optional["SRIConfig"] = None,
    env: Optional[Mapping[str, str]] = None,
) -> IndexNames:
    """Resolve index names with precedence: env var > config > default.

    ``cfg`` is accepted for forward-compatibility (config-file overrides); today
    the values come from defaults overridable per-field via the env vars listed
    in :data:`_ENV_MAP`.
    """
    env = env if env is not None else os.environ
    values: dict[str, str] = {}
    for field, default in _DEFAULTS.items():
        env_key = _ENV_MAP[field]
        cfg_val = _from_config(cfg, field)
        values[field] = env.get(env_key) or cfg_val or default
    return IndexNames(**values)


def _from_config(cfg: Optional["SRIConfig"], field: str) -> Optional[str]:
    if cfg is None:
        return None
    os_cfg = getattr(cfg, "opensearch", None)
    if os_cfg is None:
        return None
    val = getattr(os_cfg, field, None)
    return val if isinstance(val, str) and val else None
