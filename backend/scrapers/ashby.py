"""
Ashby public job board scraper.
Uses the Ashby posting API (no auth required).
"""

import logging
import time
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

COMPANIES = [
    "linear", "supabase", "loom", "retool", "mercury", "brex",
    "ramp", "notion", "cal", "dub", "cal-com", "trigger",
    "plane", "infisical", "documenso", "rallly",
    "resend", "turso", "wundergraph", "outerbase",
    "anyscale", "together-ai", "modal", "replicate",
    "baseten", "coreweave", "runway", "pika", "fal",
    "character", "perplexity", "cohere", "adept",
]

ML_KEYWORDS = {
    "machine learning", "ml engineer", "data scientist", "data science",
    "mlops", "ml platform", "ai engineer", "applied scientist",
    "research scientist", "nlp", "computer vision", "deep learning",
    "analytics engineer", "data engineer", "ml infrastructure",
    "llm", "generative ai", "applied ml", "inference", "training",
}

API_BASE = "https://api.ashbyhq.com/posting-api/job-board/{company}"
REQUEST_DELAY = 1.5


def _is_ml_role(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in ML_KEYWORDS)


def _strip_html(html: str) -> str:
    if not html:
        return ""
    try:
        return BeautifulSoup(html, "lxml").get_text(separator=" ", strip=True)
    except Exception:
        return html


def scrape(companies: list[str] = COMPANIES) -> list[dict]:
    results = []
    for company in companies:
        try:
            url = API_BASE.format(company=company)
            resp = requests.get(url, timeout=15, headers={"User-Agent": "JMI-Agent/1.0"})
            if resp.status_code != 200:
                logger.warning("Ashby %s: HTTP %s", company, resp.status_code)
                continue

            data = resp.json()
            board = data.get("jobBoard", {})
            postings = board.get("jobPostings", [])

            count = 0
            for job in postings:
                title = job.get("title", "")
                if not _is_ml_role(title):
                    continue

                location = job.get("locationName") or ""
                remote = job.get("isRemote", False) or "remote" in location.lower()
                description = _strip_html(job.get("descriptionHtml", ""))
                apply_url = job.get("applyUrl") or job.get("jobUrl") or ""

                results.append({
                    "source": "ashby",
                    "source_url": apply_url,
                    "company": board.get("name", company.title()),
                    "title": title,
                    "location": location,
                    "remote": remote,
                    "description_raw": description,
                    "posted_at": job.get("publishedDate"),
                })
                count += 1

            logger.info("Ashby %s: %d ML roles", company, count)
        except Exception as e:
            logger.error("Ashby %s error: %s", company, e)
        finally:
            time.sleep(REQUEST_DELAY)

    return results
