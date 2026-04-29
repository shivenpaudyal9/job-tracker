"""
Lever public board scraper.
Uses the Lever public postings API (no auth required).
"""

import logging
import time
from typing import Optional
import requests

logger = logging.getLogger(__name__)

COMPANIES = [
    # Streaming / media
    "netflix",
    # AI / ML
    "scale-ai", "weights-biases", "cohere", "huggingface", "together-ai",
    "coreweave", "baseten", "fal", "pika-labs", "midjourney",
    # Data / analytics
    "mixpanel", "amplitude", "segment", "rudderstack", "census-data",
    # FinTech
    "brex", "robinhood", "plaid", "ramp", "mercury",
    "modern-treasury", "moov", "unit-finance",
    # Developer tools / infra
    "gitlab", "posthog", "replit", "vercel", "netlify-inc",
    "fly-io", "railway", "neon", "upstash", "trigger-dev",
    "harness", "circleci", "mux",
    # Productivity / SaaS
    "airtable", "automattic", "nylas", "vimeo", "replicate",
    "everlaw", "elastic",
    # B2B / enterprise
    "dbt-labs", "airbyte", "confluent", "starburst",
    "prefect", "dagster-labs", "hightouch",
]

ML_KEYWORDS = {
    "machine learning", "ml", "data scientist", "data science",
    "mlops", "ai", "applied scientist", "research scientist",
    "nlp", "computer vision", "deep learning", "analytics",
    "data engineer", "llm", "generative",
}

API_BASE = "https://api.lever.co/v0/postings/{company}?mode=json"
REQUEST_DELAY = 1.5


def _is_ml_role(title: str, tags: list) -> bool:
    t = title.lower()
    tag_text = " ".join(str(tag).lower() for tag in tags)
    return any(kw in t or kw in tag_text for kw in ML_KEYWORDS)


def _extract_text(content_list: list) -> str:
    parts = []
    for item in content_list or []:
        body = item.get("body", "") if isinstance(item, dict) else str(item)
        parts.append(body)
    return "\n".join(parts)


def scrape(companies: list[str] = COMPANIES) -> list[dict]:
    results = []
    for company in companies:
        try:
            url = API_BASE.format(company=company)
            resp = requests.get(url, timeout=15, headers={"User-Agent": "JMI-Agent/1.0"})
            if resp.status_code != 200:
                logger.warning("Lever %s: HTTP %s", company, resp.status_code)
                continue

            jobs = resp.json()
            if not isinstance(jobs, list):
                continue

            count = 0
            for job in jobs:
                title = job.get("text", "")
                tags = job.get("tags", [])
                if not _is_ml_role(title, tags):
                    continue

                categories = job.get("categories", {})
                location = categories.get("location", "") or ""
                remote = "remote" in location.lower() or "remote" in [t.lower() for t in tags]

                description = _extract_text(job.get("descriptionBody", {}).get("content", []))
                if not description:
                    description = job.get("description", "")

                results.append({
                    "source": "lever",
                    "source_url": job.get("hostedUrl", ""),
                    "company": company.replace("-", " ").title(),
                    "title": title,
                    "location": location,
                    "remote": remote,
                    "description_raw": description,
                    "posted_at": None,
                })
                count += 1

            logger.info("Lever %s: %d ML roles", company, count)
        except Exception as e:
            logger.error("Lever %s error: %s", company, e)
        finally:
            time.sleep(REQUEST_DELAY)

    return results
