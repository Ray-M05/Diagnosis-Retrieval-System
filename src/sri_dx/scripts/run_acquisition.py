from pathlib import Path

from sri_dx.modules.acquisition.service import AcquisitionService
from sri_dx.adapters.scraping import (
    JsonlFileSink,
    SimpleHtmlExtractor,
    SimplePdfExtractor,
    RobotsTxtPolicy,
)
from sri_dx.adapters.scraping.http_client import HttpxClient

from sri_dx.modules.acquisition.config_loader import load_acquisition_config 


def main() -> None:
    ROOT = Path(__file__).resolve().parents[3]  # .../Diagnosis-Retrieval-System
    cfg = load_acquisition_config(ROOT / "configs" / "acquisition.yaml")

    sink_html = JsonlFileSink(cfg.out_dir / cfg.out_html_name)
    sink_pdf = JsonlFileSink(cfg.out_dir / cfg.out_pdf_name)

    svc = AcquisitionService(
        cfg=cfg,
        http=HttpxClient(cfg.user_agent, verify_ssl=cfg.verify_ssl),
        robots=RobotsTxtPolicy(),
        html_extractor=SimpleHtmlExtractor(),
        pdf_extractor=SimplePdfExtractor(),
        sink_html=sink_html,
        sink_pdf=sink_pdf,
    )

    stats = svc.run()
    print(stats)


if __name__ == "__main__":
    main()