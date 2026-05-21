from dataclasses import dataclass, replace

from sri_dx.core.ports.search.search_backend import SearchBackendPort
from sri_dx.core.schemas.search.search_request import SearchRequest, SearchFilters
from sri_dx.core.schemas.search.search_response import SearchResponse, DocumentRecord
from sri_dx.modules.indexing.concepts.extractor import ConceptExtractor


@dataclass
class SearchLexicalUseCase:
    backend: SearchBackendPort

    def search(
        self,
        *,
        query: str,
        k: int = 10,
        offset: int = 0,
        filters: SearchFilters | None = None,
        with_facets: bool = True,
        with_highlights: bool = True,
    ) -> SearchResponse:
        # Extract query concepts for expansion
        extractor = ConceptExtractor()
        concepts = extractor.extract(query)
        
        final_filters = filters or SearchFilters()
        if concepts:
            current_concepts = set(final_filters.concept_ids or [])
            current_concepts.update(concepts)
            final_filters = replace(final_filters, concept_ids=list(current_concepts))

        req = SearchRequest(
            query=query,
            k=k,
            offset=offset,
            operator="or" if concepts else "and",  # Usar OR si hay conceptos para permitir matching por concepto
            filters=final_filters,
            return_highlights=with_highlights,
            facet_fields=("source_domain", "mime_type", "seed_group") if with_facets else (),
            facet_size=20,
        )
        return self.backend.search(req)

    def get_document(self, doc_id: str) -> DocumentRecord | None:
        return self.backend.get_document(doc_id)
