"""
Greenhouse public board scraper.
Uses the undocumented-but-stable Greenhouse JSON API.
"""

import logging
import time
from typing import Optional
import requests

logger = logging.getLogger(__name__)

COMPANIES = [
    "stripe", "airbnb", "dropbox", "pinterest", "roblox", "discord",
    "figma", "notion", "openai", "anthropic", "scale", "huggingface",
    "databricks", "snowflake", "coinbase", "instacart", "doordash",
]

ML_KEYWORDS = {
    "machine learning", "ml engineer", "data scientist", "data science",
    "mlops", "ml platform", "ai engineer", "applied scientist",
    "research scientist", "nlp", "computer vision", "deep learning",
    "analytics engineer", "data engineer", "ml infrastructure",
    "llm", "generative ai", "applied ml",
}

API_BASE = "https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
REQUEST_DELAY = 1.5  # seconds between company requests


def _is_ml_role(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in ML_KEYWORDS)


def _parse_location(job: dict) -> tuple[str, bool]:
    loc = job.get("location", {})
    name = loc.get("name", "") if isinstance(loc, dict) else str(loc)
    remote = "remote" in name.lower()
    return name, remote


def scrape(companies: list[str] = COMPANIES) -> list[dict]:
    results = []
    for company in companies:
        try:
            url = API_BASE.format(company=company)
            resp = requests.get(url, timeout=15, headers={"User-Agent": "JMI-Agent/1.0"})
            if resp.status_code != 200:
                logger.warning("Greenhouse %s: HTTP %s", company, resp.status_code)
                continue

            data = resp.json()
            jobs = data.get("jobs", [])
            count = 0
            for job in jobs:
                title = job.get("title", "")
                if not _is_ml_role(title):
                    continue

                location, remote = _parse_location(job)
                content = job.get("content", "") or ""

                results.append({
                    "source": "greenhouse",
                    "source_url": job.get("absolute_url", ""),
                    "company": company.title(),
                    "title": title,
                    "location": location,
                    "remote": remote,
                    "description_raw": content,
                    "posted_at": job.get("updated_at"),
                })
                count += 1

            logger.info("Greenhouse %s: %d ML roles", company, count)
        except Exception as e:
            logger.error("Greenhouse %s error: %s", company, e)
        finally:
            time.sleep(REQUEST_DELAY)

    return results
