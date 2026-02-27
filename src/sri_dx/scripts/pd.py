from pathlib import Path

from sri_dx.modules.acquisition import AcquisitionConfig, Seed, AcquisitionService
from sri_dx.adapters.scraping import (
    JsonlFileSink,
    SimpleHtmlExtractor,
    SimplePdfExtractor,
    RobotsTxtPolicy,
)

from sri_dx.adapters.scraping.http_client import HttpxClient


def main():
    cfg = AcquisitionConfig(
        whitelist_domains=("example.com", "www.w3.org"),
        seeds=(
            Seed("seed_001", "demo", "https://example.com"),
            Seed("seed_002", "demo", "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"),
        ),
        max_depth=0,          # SOLO seeds para probar
        max_docs=10,
        per_domain_delay_s=0, # rápido para test
        out_dir=Path("data/processed"),
    )

    sink_html = JsonlFileSink(cfg.out_dir / cfg.out_html_name)
    sink_pdf = JsonlFileSink(cfg.out_dir / cfg.out_pdf_name)

    http = HttpxClient(cfg.user_agent)  # <- tu entorno
    robots = RobotsTxtPolicy()

    svc = AcquisitionService(
        cfg=cfg,
        http=http,
        robots=robots,
        html_extractor=SimpleHtmlExtractor(),
        pdf_extractor=SimplePdfExtractor(),
        sink_html=sink_html,
        sink_pdf=sink_pdf,
    )

    stats = svc.run()
    print(stats)
    print("OK step6 run")


if __name__ == "__main__":
    main()