from .schemas.acquisition_config import AcquisitionConfig, Seed
from .models import CrawlTask
from sri_dx.core.schemas.acquisition.acquired_document import Section
from sri_dx.core.schemas.acquisition.fetch_result import FetchResult
from sri_dx.core.ports.acquisition import (
    HttpClientPort as HttpClient,
    RobotsPolicyPort as RobotsPolicy,
    HtmlExtractorPort as HtmlExtractor,
    PdfExtractorPort as PdfExtractor,
    JsonlSinkPort as JsonlSink,
)
from .config_loader import load_acquisition_config
from .service import AcquisitionService

__all__ = [
    "AcquisitionConfig",
    "Seed",
    "CrawlTask",
    "FetchResult",
    "Section",
    "HttpClient",
    "RobotsPolicy",
    "HtmlExtractor",
    "PdfExtractor",
    "JsonlSink",
    "load_acquisition_config",
    "AcquisitionService",
]