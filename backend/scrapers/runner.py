"""
Orchestrator: runs all scrapers, deduplicates by source_url, returns combined list.
Called by the daily scrape cron job.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from scrapers import greenhouse, lever, linkedin, ashby

logger = logging.getLogger(__name__)


def run_all(
    run_greenhouse: bool = True,
    run_lever: bool = True,
    run_linkedin: bool = True,
    run_ashby: bool = True,
) -> list[dict]:
    all_postings: list[dict] = []
    seen_urls: set[str] = set()

    def _add(postings: list[dict], source: str):
        added = 0
        for p in postings:
            url = p.get("source_url", "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            all_postings.append(p)
            added += 1
        logger.info("%s: %d unique postings collected", source, added)

    # Boards are independent. Run at most three provider loops concurrently;
    # each provider still honors its own per-company delay/rate limit.
    providers = [
        ("Greenhouse", greenhouse.scrape, run_greenhouse),
        ("Lever", lever.scrape, run_lever),
        ("LinkedIn", linkedin.scrape, run_linkedin),
        ("Ashby", ashby.scrape, run_ashby),
    ]
    enabled = [(name, scrape_fn) for name, scrape_fn, on in providers if on]
    if enabled:
        with ThreadPoolExecutor(max_workers=min(3, len(enabled))) as pool:
            pending = {pool.submit(fn): name for name, fn in enabled}
            for future in as_completed(pending):
                name = pending[future]
                try:
                    # Merge and deduplicate on the calling thread, never inside workers.
                    _add(future.result(), name)
                except Exception as e:
                    logger.error("%s scraper failed: %s", name, e)

    logger.info("Total unique postings from all sources: %d", len(all_postings))
    return all_postings
