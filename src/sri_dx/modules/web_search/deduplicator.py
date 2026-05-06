"""
Deduplication is performed at four levels (in order of priority):
1. Bibliographic identity: PMID, PMCID, DOI.
2. Normalised canonical URL.
3. ``doc_id`` derived from the canonical URL.
4. ``content_hash`` of the cleaned body.
"""
from __future__ import annotations

import logging

from sri_dx.modules.web_search.schemas import ExternalApiDocument

logger = logging.getLogger(__name__)


def identity_keys(ext: ExternalApiDocument) -> frozenset[str]:
    """
    Return the set of opaque identity keys for *ext*.

    Two documents that share any key are considered duplicates.
    """
    keys: list[str] = []
    if ext.pmid:
        keys.append(f"pmid:{ext.pmid}")
    if ext.pmcid:
        keys.append(f"pmcid:{ext.pmcid}")
    if ext.doi:
        keys.append(f"doi:{ext.doi.lower()}")
    if ext.canonical_url:
        keys.append(f"url:{ext.canonical_url}")
    return frozenset(keys)


class ApiDocumentDeduplicator:
    """
    Stateful deduplicator for a single web-search session.

    Parameters
    ----------
    existing_content_hashes:
        ``content_hash`` values already present in the OpenSearch index.
    existing_identity_keys:
        Flattened identity keys (PMID/PMCID/DOI/URL strings) already present
        in the OpenSearch index.  Can be empty when the corpus check is skipped.
    """

    def __init__(
        self,
        existing_content_hashes: set[str] | None = None,
        existing_identity_keys: set[str] | None = None,
    ) -> None:
        self._existing_hashes: set[str] = existing_content_hashes or set()
        self._existing_keys: set[str] = existing_identity_keys or set()

        # Session-level accumulators (within a single API fetch)
        self._seen_hashes: set[str] = set()
        self._seen_keys: set[str] = set()

    def should_keep(
        self,
        ext: ExternalApiDocument,
        acquired_dict: dict,
    ) -> bool:
        """
        Return ``True`` when the document is new and should be indexed.

        Side-effect: if the document is kept, its identity keys and content
        hash are added to the session-level seen sets.
        """
        keys = identity_keys(ext)
        ch: str = acquired_dict.get("content_hash", "")

        # --- check against already-indexed corpus ---
        if keys & self._existing_keys:
            logger.debug(
                "Dedup: skipping '%s' — identity key already in index", ext.title[:60]
            )
            return False

        if ch and ch in self._existing_hashes:
            logger.debug(
                "Dedup: skipping '%s' — content_hash already in index", ext.title[:60]
            )
            return False

        # --- check within current session ---
        if keys & self._seen_keys:
            logger.debug(
                "Dedup: skipping '%s' — duplicate within session (keys)", ext.title[:60]
            )
            return False

        if ch and ch in self._seen_hashes:
            logger.debug(
                "Dedup: skipping '%s' — duplicate within session (hash)", ext.title[:60]
            )
            return False

        # New document — register it
        self._seen_keys.update(keys)
        if ch:
            self._seen_hashes.add(ch)
        return True

    def filter(
        self,
        pairs: list[tuple[ExternalApiDocument, dict]],
    ) -> list[tuple[ExternalApiDocument, dict]]:
        """
        Filter a list of ``(ExternalApiDocument, acquired_dict)`` pairs,
        returning only those that should be kept.

        Parameters
        ----------
        pairs:
            Each tuple contains the external document and its already-computed
            ``acquired_dict`` (output of :func:`external_to_acquired_dict`).
        """
        kept = [
            (ext, doc)
            for ext, doc in pairs
            if self.should_keep(ext, doc)
        ]
        removed = len(pairs) - len(kept)
        if removed:
            logger.info("Dedup: removed %d duplicate(s), kept %d", removed, len(kept))
        return kept
