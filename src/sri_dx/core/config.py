import os
import tomllib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Optional

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
class SRIConfig:
    opensearch: OpenSearchConfig = field(default_factory=OpenSearchConfig)
    indexing: IndexingConfig = field(default_factory=IndexingConfig)

def load_config(config_path: Optional[Path] = None) -> SRIConfig:
    """Loads configuration from a TOML file and environment variables."""
    data: dict[str, Any] = {}
    
    # Load from file if exists
    path = config_path or Path("config.toml")
    if path.exists():
        with open(path, "rb") as f:
            data = tomllib.load(f)
            
    # OpenSearch setup
    os_data = data.get("opensearch", {})
    opensearch = OpenSearchConfig(
        host=os.environ.get("SRI_OS_HOST", os_data.get("host", "localhost")),
        port=int(os.environ.get("SRI_OS_PORT", os_data.get("port", 9200))),
        use_ssl=os.environ.get("SRI_OS_SSL", str(os_data.get("use_ssl", "false"))).lower() == "true",
        verify_certs=os.environ.get("SRI_OS_VERIFY", str(os_data.get("verify_certs", "false"))).lower() == "true",
        index_name=os.environ.get("SRI_OS_INDEX", os_data.get("index_name", "clinical_docs_v1")),
        alias_name=os.environ.get("SRI_OS_ALIAS", os_data.get("alias_name", "clinical_docs")),
    )
    
    # Indexing setup
    idx_data = data.get("indexing", {})
    indexing = IndexingConfig(
        html_source=Path(os.environ.get("SRI_HTML_SRC", idx_data.get("html_source", "data/processed/docs_html.jsonl"))),
        pdf_source=Path(os.environ.get("SRI_PDF_SRC", idx_data.get("pdf_source", "data/processed/docs_pdf.jsonl"))),
        manifest_path=Path(os.environ.get("SRI_MANIFEST", idx_data.get("manifest_path", "data/index/manifest.sqlite"))),
        report_dir=Path(os.environ.get("SRI_REPORT_DIR", idx_data.get("report_dir", "data/index/reports"))),
        bad_docs_path=Path(os.environ.get("SRI_BAD_DOCS", idx_data.get("bad_docs_path", "data/index/bad_docs.jsonl"))),
        batch_size=int(os.environ.get("SRI_BATCH_SIZE", idx_data.get("batch_size", 500))),
    )
    
    return SRIConfig(opensearch=opensearch, indexing=indexing)
