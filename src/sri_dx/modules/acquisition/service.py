from __future__ import annotations

import time
from collections import deque
from typing import Optional

from .config import AcquisitionConfig, Seed
from .models import CrawlTask
from .ports import HttpClient, RobotsPolicy, HtmlExtractor, PdfExtractor, JsonlSink
from . import urls as url_utils
from .document_factory import build_document


class AcquisitionService:
    """
    Orquestador end-to-end del módulo de adquisición.

    Flujo:
      seeds -> frontier
      pop -> filtros (visited/deny/whitelist) -> robots -> http.get
      -> extractor (html/pdf) -> build_document -> sink JSONL por tipo
      -> si HTML: expand out_links (depth < max_depth)
    """

    def __init__(
        self,
        *,
        cfg: AcquisitionConfig,
        http: HttpClient,
        robots: RobotsPolicy,
        html_extractor: HtmlExtractor,
        pdf_extractor: PdfExtractor,
        sink_html: JsonlSink,
        sink_pdf: JsonlSink,
    ) -> None:
        self.cfg = cfg
        self.http = http
        self.robots = robots
        self.html_extractor = html_extractor
        self.pdf_extractor = pdf_extractor
        self.sink_html = sink_html
        self.sink_pdf = sink_pdf

        self._visited: set[str] = set()
        self._seen_hashes: set[str] = set()  # dedupe por contenido

    def run(self) -> dict:
        frontier = deque(self._seed_tasks())
        written_html = 0
        written_pdf = 0
        visited_total = 0

        while frontier and (written_html + written_pdf) < self.cfg.max_docs:
            task = frontier.popleft()
            url = url_utils.normalize_url(task.url)

            # visited
            if url in self._visited:
                continue
            self._visited.add(url)
            visited_total += 1

            # denylist + whitelist
            if url_utils.is_denied(url):
                continue
            if not url_utils.within_whitelist(url, self.cfg.whitelist_domains):
                continue

            # robots
            if not self.robots.allowed(url, self.cfg.user_agent):
                continue

            # politeness (simple)
            if self.cfg.per_domain_delay_s > 0:
                time.sleep(self.cfg.per_domain_delay_s)

            # fetch
            try:
                fr = self.http.get(url, timeout_s=self.cfg.timeout_s)
            except Exception:
                continue

            if fr.status_code >= 400 or not fr.content:
                continue

            mime = (fr.mime_type or "").split(";")[0].strip().lower()

            # parse + extract
            title: Optional[str] = None
            sections = []
            body = ""
            out_links: list[str] = []
            meta_partial: dict = {}

            try:
                if mime.startswith("text/html"):
                    title, sections, body, out_links, meta_partial = self.html_extractor.extract(fr.url, fr.content)
                elif mime == "application/pdf":
                    title, sections, body, meta_partial = self.pdf_extractor.extract(fr.url, fr.content)
                else:
                    # tipo no soportado
                    continue
            except Exception:
                continue

            # build final document dict (incluye cleaning + hashes)
            try:
                doc = build_document(
                    task=task,
                    final_url=fr.url,
                    mime_type=mime,
                    fetched_at=fr.fetched_at,
                    title=title,
                    sections=sections,
                    body=body,
                    page_meta_partial=meta_partial,
                )
            except Exception:
                continue

            # dedupe por contenido (opcional pero útil con 2000 docs)
            ch = doc.get("content_hash")
            if isinstance(ch, str) and ch in self._seen_hashes:
                # Igual puedes expandir links si quieres; aquí lo hacemos igual.
                pass
            else:
                if isinstance(ch, str):
                    self._seen_hashes.add(ch)

                # persist JSONL por tipo
                if mime.startswith("text/html"):
                    self.sink_html.write(doc)
                    written_html += 1
                else:
                    self.sink_pdf.write(doc)
                    written_pdf += 1

            # expand links (solo HTML)
            if mime.startswith("text/html") and task.depth < self.cfg.max_depth:
                for href in out_links:
                    nxt = url_utils.absolutize(fr.url, href)
                    if not nxt:
                        continue
                    # filtros antes de encolar (más barato)
                    if url_utils.is_denied(nxt):
                        continue
                    if not url_utils.within_whitelist(nxt, self.cfg.whitelist_domains):
                        continue
                    if nxt in self._visited:
                        continue

                    frontier.append(
                        CrawlTask(
                            url=nxt,
                            depth=task.depth + 1,
                            parent_url=fr.url,
                            seed_id=task.seed_id,
                            seed_group=task.seed_group,
                        )
                    )

        return {
            "written_html": written_html,
            "written_pdf": written_pdf,
            "visited_total": visited_total,
            "unique_hashes": len(self._seen_hashes),
        }

    def _seed_tasks(self) -> list[CrawlTask]:
        tasks: list[CrawlTask] = []
        for seed in self.cfg.seeds:
            tasks.append(
                CrawlTask(
                    url=seed.url,
                    depth=0,
                    parent_url=None,
                    seed_id=seed.seed_id,
                    seed_group=seed.seed_group,
                )
            )
        return tasks