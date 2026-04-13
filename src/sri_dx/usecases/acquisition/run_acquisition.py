from dataclasses import dataclass

from sri_dx.modules.acquisition.service import AcquisitionService
from sri_dx.modules.acquisition.schemas.acquisition_config import AcquisitionConfig
from sri_dx.core.ports.acquisition.http_client_port import HttpClientPort
from sri_dx.core.ports.acquisition.robots_policy_port import RobotsPolicyPort
from sri_dx.core.ports.acquisition.html_extractor_port import HtmlExtractorPort
from sri_dx.core.ports.acquisition.pdf_extractor_port import PdfExtractorPort
from sri_dx.core.ports.acquisition.jsonl_sink_port import JsonlSinkPort


@dataclass
class RunAcquisitionUseCase:
    cfg: AcquisitionConfig
    http: HttpClientPort
    robots: RobotsPolicyPort
    html_extractor: HtmlExtractorPort
    pdf_extractor: PdfExtractorPort
    sink_html: JsonlSinkPort
    sink_pdf: JsonlSinkPort

    async def execute(self) -> dict:
        svc = AcquisitionService(
            cfg=self.cfg,
            http=self.http,
            robots=self.robots,
            html_extractor=self.html_extractor,
            pdf_extractor=self.pdf_extractor,
            sink_html=self.sink_html,
            sink_pdf=self.sink_pdf,
        )
        return await svc.run()
