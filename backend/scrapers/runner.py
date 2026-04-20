"""
Orchestrator: runs all scrapers, deduplicates by source_url, returns combined list.
Called by the daily scrape cron job.
"""

import logging
from typing import Optional

from scrapers import greenhouse, lever, linkedin

logger = logging.getLogger(__name__)


def run_all(
    run_greenhouse: bool = True,
    run_lever: bool = True,
    run_linkedin: bool = True,
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

    if run_greenhouse:
        try:
            _add(greenhouse.scrape(), "Greenhouse")
        except Exception as e:
            logger.error("Greenhouse scraper failed: %s", e)

    if run_lever:
        try:
            _add(lever.scrape(), "Lever")
        except Exception as e:
            logger.error("Lever scraper failed: %s", e)

    if run_linkedin:
        try:
            _add(linkedin.scrape(), "LinkedIn")
        except Exception as e:
            logger.error("LinkedIn scraper failed: %s", e)

    logger.info("Total unique postings from all sources: %d", len(all_postings))
    return all_postings
