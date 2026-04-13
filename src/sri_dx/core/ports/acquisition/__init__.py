# Ports para el módulo de Acquisition
# Interfaces para obtención y persistencia de documentos

from .document_sink import IndexDocumentSinkPort
from .document_source import DocumentSourcePort
from .manifest_store import ManifestStorePort
from .http_client_port import HttpClientPort
from .robots_policy_port import RobotsPolicyPort
from .html_extractor_port import HtmlExtractorPort
from .pdf_extractor_port import PdfExtractorPort
from .jsonl_sink_port import JsonlSinkPort

__all__ = [
    "IndexDocumentSinkPort",
    "DocumentSourcePort",
    "ManifestStorePort",
    "HttpClientPort",
    "RobotsPolicyPort",
    "HtmlExtractorPort",
    "PdfExtractorPort",
    "JsonlSinkPort",
]
