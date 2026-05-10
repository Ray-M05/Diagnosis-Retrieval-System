import os
import tomllib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Optional, List

@dataclass(frozen=True)
class OpenSearchConfig:
    host: str = "localhost"
    port: int = 9200
    use_ssl: bool = False
    verify_certs: bool = False
    index_name: str = "clinical_docs_v1"
    alias_name: str = "clinical_docs"
    request_timeout: int = 30

@dataclass(frozen=True)
class IndexingConfig:
    html_source: Path = Path("data/processed/docs_html.jsonl")
    pdf_source: Path = Path("data/processed/docs_pdf.jsonl")
    manifest_path: Path = Path("data/index/manifest.sqlite")
    report_dir: Path = Path("data/index/reports")
    bad_docs_path: Path = Path("data/index/bad_docs.jsonl")
    batch_size: int = 500

@dataclass(frozen=True)
class RAGConfig:
    default_model: str = "llama-3.1-8b-instant"
    groq_api_key: str = ""
    max_context_chunks: int = 10
    max_output_tokens: int = 1500
    temperature: float = 0.2
    include_disease_hints: bool = True

@dataclass(frozen=True)
class APIConfig:
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: List[str] = field(default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"])

@dataclass(frozen=True)
class WebSearchSufficiencyConfig:
    """Thresholds used by LocalSufficiencyEvaluator."""
    theta_rank_confidence: float = 0.55
    theta_useful_doc_score: float = 0.50
    min_useful_docs: int = 3
    theta_symptom_coverage: float = 0.60
    min_source_diversity: int = 2
    theta_insufficiency: float = 0.45

@dataclass(frozen=True)
class WebSearchConfig:
    """Configuration for the web search & enrich module."""
    enabled: bool = True
    retmax_medlineplus: int = 8
    retmax_europe_pmc: int = 8
    retmax_pubmed: int = 5
    delta_dir: Path = Path("data/processed/api_deltas")
    report_dir: Path = Path("data/web_search/reports")
    http_timeout: float = 20.0
    sufficiency: WebSearchSufficiencyConfig = field(default_factory=WebSearchSufficiencyConfig)

@dataclass(frozen=True)
class SRIConfig:
    opensearch: OpenSearchConfig = field(default_factory=OpenSearchConfig)
    indexing: IndexingConfig = field(default_factory=IndexingConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    api: APIConfig = field(default_factory=APIConfig)
    web_search: WebSearchConfig = field(default_factory=WebSearchConfig)

def load_config(config_path: Optional[Path] = None) -> SRIConfig:
    """Loads configuration from a TOML file and environment variables."""
    data: dict[str, Any] = {}

    path = config_path or Path("config.toml")
    if path.exists():
        with open(path, "rb") as f:
            data = tomllib.load(f)

    os_data = data.get("opensearch", {})
    opensearch = OpenSearchConfig(
        host=os.environ.get("SRI_OS_HOST", os_data.get("host", "localhost")),
        port=int(os.environ.get("SRI_OS_PORT", os_data.get("port", 9200))),
        use_ssl=os.environ.get("SRI_OS_SSL", str(os_data.get("use_ssl", "false"))).lower() == "true",
        verify_certs=os.environ.get("SRI_OS_VERIFY", str(os_data.get("verify_certs", "false"))).lower() == "true",
        index_name=os.environ.get("SRI_OS_INDEX", os_data.get("index_name", "clinical_docs_v1")),
        alias_name=os.environ.get("SRI_OS_ALIAS", os_data.get("alias_name", "clinical_docs")),
    )

    idx_data = data.get("indexing", {})
    indexing = IndexingConfig(
        html_source=Path(os.environ.get("SRI_HTML_SRC", idx_data.get("html_source", "data/processed/docs_html.jsonl"))),
        pdf_source=Path(os.environ.get("SRI_PDF_SRC", idx_data.get("pdf_source", "data/processed/docs_pdf.jsonl"))),
        manifest_path=Path(os.environ.get("SRI_MANIFEST", idx_data.get("manifest_path", "data/index/manifest.sqlite"))),
        report_dir=Path(os.environ.get("SRI_REPORT_DIR", idx_data.get("report_dir", "data/index/reports"))),
        bad_docs_path=Path(os.environ.get("SRI_BAD_DOCS", idx_data.get("bad_docs_path", "data/index/bad_docs.jsonl"))),
        batch_size=int(os.environ.get("SRI_BATCH_SIZE", idx_data.get("batch_size", 500))),
    )

    rag_data = data.get("rag", {})
    rag = RAGConfig(
        default_model=os.environ.get("SRI_RAG_MODEL", rag_data.get("default_model", "llama-3.1-8b-instant")),
        groq_api_key=os.environ.get("GROQ_API_KEY", rag_data.get("groq_api_key", "")),
        max_context_chunks=int(os.environ.get("SRI_RAG_MAX_CHUNKS", rag_data.get("max_context_chunks", 10))),
        max_output_tokens=int(os.environ.get("SRI_RAG_MAX_TOKENS", rag_data.get("max_output_tokens", 1500))),
        temperature=float(os.environ.get("SRI_RAG_TEMPERATURE", rag_data.get("temperature", 0.2))),
        include_disease_hints=os.environ.get(
            "SRI_RAG_DISEASE_HINTS", str(rag_data.get("include_disease_hints", True))
        ).lower() != "false",
    )

    api_data = data.get("api", {})
    cors_raw = os.environ.get("SRI_CORS_ORIGINS", "")
    cors_origins = (
        [o.strip() for o in cors_raw.split(",") if o.strip()]
        if cors_raw
        else api_data.get("cors_origins", ["http://localhost:5173", "http://localhost:3000"])
    )
    api = APIConfig(
        host=os.environ.get("SRI_API_HOST", api_data.get("host", "127.0.0.1")),
        port=int(os.environ.get("SRI_API_PORT", api_data.get("port", 8000))),
        cors_origins=cors_origins,
    )

    ws_data = data.get("web_search", {})
    suf_data = ws_data.get("sufficiency", {})
    sufficiency_cfg = WebSearchSufficiencyConfig(
        theta_rank_confidence=float(suf_data.get("theta_rank_confidence", 0.55)),
        theta_useful_doc_score=float(suf_data.get("theta_useful_doc_score", 0.50)),
        min_useful_docs=int(suf_data.get("min_useful_docs", 3)),
        theta_symptom_coverage=float(suf_data.get("theta_symptom_coverage", 0.60)),
        min_source_diversity=int(suf_data.get("min_source_diversity", 2)),
        theta_insufficiency=float(suf_data.get("theta_insufficiency", 0.45)),
    )
    web_search_cfg = WebSearchConfig(
        enabled=ws_data.get("enabled", True),
        retmax_medlineplus=int(ws_data.get("retmax_medlineplus", 8)),
        retmax_europe_pmc=int(ws_data.get("retmax_europe_pmc", 8)),
        retmax_pubmed=int(ws_data.get("retmax_pubmed", 5)),
        delta_dir=Path(ws_data.get("delta_dir", "data/processed/api_deltas")),
        report_dir=Path(ws_data.get("report_dir", "data/web_search/reports")),
        http_timeout=float(ws_data.get("http_timeout", 20.0)),
        sufficiency=sufficiency_cfg,
    )

    return SRIConfig(opensearch=opensearch, indexing=indexing, rag=rag, api=api, web_search=web_search_cfg)
