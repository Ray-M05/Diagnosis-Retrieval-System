from __future__ import annotations

import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from typing import Optional
import json
from pathlib import Path

from .schemas.acquisition_config import AcquisitionConfig
from .models import CrawlTask
from sri_dx.core.ports.acquisition import (
    HttpClientPort,
    RobotsPolicyPort,
    HtmlExtractorPort,
    PdfExtractorPort,
    JsonlSinkPort,
)
from . import urls as url_utils
from .document_factory import build_document
from .persist_policy import should_persist


class AcquisitionService:
    """
    Orquestador end-to-end del módulo de adquisición.

    Flujo:
      seeds -> frontier
      pop -> filtros (visited/deny/whitelist) -> robots -> http.get
      -> extractor (html/pdf) -> build_document
      -> (persist_policy decide si se guarda)
      -> si HTML: expand out_links (depth < max_depth)

    Concurrency model:
      - cfg.max_workers workers run in a ThreadPoolExecutor.
      - Workers NEVER sleep. They only do network I/O + CPU extraction.
      - Per-domain rate limiting is enforced by the scheduler (_submit_from_frontier)
        running in the main thread: if a domain is still cooling down its slot is
        skipped and the task is re-queued, so other domains keep running.
      - The main loop runs until both `pending` AND `frontier` are exhausted,
        avoiding premature exit when a domain cooldown temporarily empties the pool.
    """

    def __init__(
        self,
        *,
        cfg: AcquisitionConfig,
        http: HttpClientPort,
        robots: RobotsPolicyPort,
        html_extractor: HtmlExtractorPort,
        pdf_extractor: PdfExtractorPort,
        sink_html: JsonlSinkPort,
        sink_pdf: JsonlSinkPort,
    ) -> None:
        self.cfg = cfg
        self.http = http
        self.robots = robots
        self.html_extractor = html_extractor
        self.pdf_extractor = pdf_extractor
        self.sink_html = sink_html
        self.sink_pdf = sink_pdf

        self._visited: set[str] = set()
        self._seen_hashes: set[str] = set()

        self._load_existing_hashes()

    def _load_existing_hashes(self) -> None:
        """
        Carga los content_hash de documentos ya guardados en los archivos JSONL.
        Esto previene duplicados entre múltiples ejecuciones del crawler.
        """
        for path in (
            Path(self.cfg.out_dir) / self.cfg.out_html_name,
            Path(self.cfg.out_dir) / self.cfg.out_pdf_name,
        ):
            if not path.exists():
                continue
            try:
                with path.open("r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            doc = json.loads(line)
                            ch = doc.get("content_hash")
                            if isinstance(ch, str) and ch:
                                self._seen_hashes.add(ch)
                        except json.JSONDecodeError:
                            continue
            except Exception:
                pass

    def _process_task(
        self, task: CrawlTask
    ) -> tuple[list[CrawlTask], dict | None, str | None, int]:
        """
        Fetch + extract + build for one URL.
        No sleeping here — rate limiting is done by the scheduler in run().
        Thread-safe: reads only immutable config and stateless adapters.
        """
        url = url_utils.normalize_url(task.url)

        if not self.robots.allowed(url, self.cfg.user_agent):
            return [], None, None, 0

        try:
            fr = self.http.get(url, timeout_s=self.cfg.timeout_s)
        except Exception:
            return [], None, None, 0

        if fr.status_code >= 400 or not fr.content:
            return [], None, None, 0

        mime = (fr.mime_type or "").split(";")[0].strip().lower()

        title: Optional[str] = None
        sections = []
        body = ""
        out_links: list[str] = []
        meta_partial: dict = {}

        try:
            if mime.startswith("text/html"):
                title, sections, body, out_links, meta_partial = (
                    self.html_extractor.extract(fr.url, fr.content)
                )
            elif mime == "application/pdf":
                title, sections, body, meta_partial = self.pdf_extractor.extract(
                    fr.url, fr.content
                )
            else:
                return [], None, None, 0
        except Exception:
            return [], None, None, 0

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
            return [], None, None, 0

        candidate_tasks: list[CrawlTask] = []
        if mime.startswith("text/html") and task.depth < self.cfg.max_depth:
            for href in out_links:
                nxt = url_utils.absolutize(fr.url, href)
                if not nxt:
                    continue
                if url_utils.is_denied(nxt):
                    continue
                if not url_utils.within_whitelist(nxt, self.cfg.whitelist_domains):
                    continue
                candidate_tasks.append(
                    CrawlTask(
                        url=nxt,
                        depth=task.depth + 1,
                        parent_url=fr.url,
                        seed_id=task.seed_id,
                        seed_group=task.seed_group,
                    )
                )

        return candidate_tasks, doc, mime, len(out_links)

    def run(self) -> dict:
        frontier: deque[CrawlTask] = deque(self._seed_tasks())
        written_html = 0
        written_pdf = 0
        visited_total = 0
        skipped_not_persisted = 0
        skipped_duplicates = 0
        max_workers = self.cfg.max_workers
        cfg_delay = self.cfg.per_domain_delay_s
        # Tracks earliest time (monotonic) the next request to each domain may be sent.
        domain_next_time: dict[str, float] = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            pending: dict = {}

            def _submit_from_frontier() -> None:
                """
                Pull tasks from frontier, apply cheap filters + non-blocking
                per-domain rate limit, then submit to the thread pool.

                Tasks for domains that are still cooling down are deferred back
                to the front of the frontier so they are retried on the next
                scheduling cycle without blocking any worker thread.
                """
                nonlocal visited_total
                deferred: list[CrawlTask] = []

                while frontier and len(pending) < max_workers * 2:
                    task = frontier.popleft()
                    url = url_utils.normalize_url(task.url)

                    if url in self._visited:
                        continue
                    if url_utils.is_denied(url):
                        continue
                    if not url_utils.within_whitelist(url, self.cfg.whitelist_domains):
                        continue

                    # Non-blocking domain rate limit
                    if cfg_delay > 0:
                        domain = url_utils.get_domain(url)
                        now = time.monotonic()
                        if now < domain_next_time.get(domain, 0.0):
                            # Domain cooling down — defer and try next task
                            deferred.append(task)
                            continue
                        # Claim this slot for the domain immediately
                        domain_next_time[domain] = now + cfg_delay

                    self._visited.add(url)
                    visited_total += 1
                    f = executor.submit(self._process_task, task)
                    pending[f] = task

                # Re-queue deferred tasks at the front so they are tried first
                for t in reversed(deferred):
                    frontier.appendleft(t)

            _submit_from_frontier()

            # Keep going until both the pool AND the frontier are drained.
            # Using only `while pending` would cause premature exit when all
            # workers finish but the frontier still has tasks waiting for a
            # domain cooldown to expire.
            while pending or frontier:
                if pending:
                    done_set, _ = wait(
                        list(pending.keys()), timeout=1.0, return_when=FIRST_COMPLETED
                    )
                else:
                    # No active workers: all frontier tasks are domain-throttled.
                    # Sleep briefly then let _submit_from_frontier retry.
                    time.sleep(0.5)
                    done_set = set()

                for f in done_set:
                    pending.pop(f, None)
                    try:
                        candidate_tasks, doc, mime, out_links_count = f.result()
                    except Exception:
                        continue

                    if doc is None:
                        continue

                    try:
                        persist = should_persist(
                            url=doc["url"],
                            mime_type=mime,
                            body=doc["content"]["body"],
                            out_links_count=out_links_count if mime.startswith("text/html") else 0,
                            cfg=self.cfg,
                        )
                    except Exception:
                        persist = True

                    if persist:
                        ch = doc.get("content_hash")
                        if isinstance(ch, str) and ch in self._seen_hashes:
                            skipped_duplicates += 1
                        else:
                            if isinstance(ch, str) and ch:
                                self._seen_hashes.add(ch)
                            if mime.startswith("text/html"):
                                self.sink_html.write(doc)
                                written_html += 1
                            else:
                                self.sink_pdf.write(doc)
                                written_pdf += 1
                    else:
                        skipped_not_persisted += 1

                    if (written_html + written_pdf) >= self.cfg.max_docs:
                        # Cancel remaining pending tasks and stop expanding frontier
                        for remaining in list(pending.keys()):
                            remaining.cancel()
                        pending.clear()
                        frontier.clear()
                        break

                    for t in candidate_tasks:
                        if url_utils.normalize_url(t.url) not in self._visited:
                            frontier.append(t)

                if (written_html + written_pdf) < self.cfg.max_docs:
                    _submit_from_frontier()

        return {
            "written_html": written_html,
            "written_pdf": written_pdf,
            "visited_total": visited_total,
            "unique_hashes": len(self._seen_hashes),
            "skipped_not_persisted": skipped_not_persisted,
            "skipped_duplicates": skipped_duplicates,
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
