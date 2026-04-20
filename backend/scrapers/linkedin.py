"""
LinkedIn scraper — uses cloudscraper to bypass basic bot detection.
Targets the public job search endpoint. Rate-limited to 1 req/5s.
Fails gracefully: blocked requests are logged and skipped, never crash the pipeline.
"""

import logging
import time
import re
from typing import Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

ML_QUERIES = [
    "machine learning engineer",
    "data scientist",
    "MLOps engineer",
    "applied scientist",
    "NLP engineer",
]

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
REQUEST_DELAY = 5  # seconds — respect rate limits
MAX_RESULTS_PER_QUERY = 25


def _try_import_cloudscraper():
    try:
        import cloudscraper
        return cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
    except ImportError:
        logger.warning("cloudscraper not installed — LinkedIn scraper disabled")
        return None


def _parse_job_card(card_html: str) -> Optional[dict]:
    try:
        # Extract job details from the HTML snippet LinkedIn returns
        title_match = re.search(r'class="base-search-card__title[^"]*"[^>]*>([^<]+)<', card_html)
        company_match = re.search(r'class="base-search-card__subtitle[^"]*"[^>]*>\s*<[^>]*>([^<]+)<', card_html)
        location_match = re.search(r'class="job-search-card__location[^"]*"[^>]*>([^<]+)<', card_html)
        url_match = re.search(r'href="(https://www\.linkedin\.com/jobs/view/[^"?]+)', card_html)

        if not title_match or not url_match:
            return None

        title = title_match.group(1).strip()
        company = company_match.group(1).strip() if company_match else "Unknown"
        location = location_match.group(1).strip() if location_match else ""
        url = url_match.group(1).strip()

        return {
            "source": "linkedin",
            "source_url": url,
            "company": company,
            "title": title,
            "location": location,
            "remote": "remote" in location.lower(),
            "description_raw": f"{title} at {company}. Location: {location}",
            "posted_at": None,
        }
    except Exception:
        return None


def scrape(queries: list[str] = ML_QUERIES) -> list[dict]:
    scraper = _try_import_cloudscraper()
    if not scraper:
        return []

    results = []
    seen_urls = set()

    for query in queries:
        try:
            params = {
                "keywords": query,
                "location": "United States",
                "f_TPR": "r604800",  # last 7 days
                "start": 0,
            }
            url = f"{SEARCH_URL}?{urlencode(params)}"
            resp = scraper.get(url, timeout=20)

            if resp.status_code == 429:
                logger.warning("LinkedIn rate limited — skipping remaining queries")
                break
            if resp.status_code != 200:
                logger.warning("LinkedIn query '%s': HTTP %s — skipping", query, resp.status_code)
                time.sleep(REQUEST_DELAY)
                continue

            # LinkedIn returns raw HTML job cards
            html = resp.text
            card_pattern = re.compile(r'<li[^>]*>(.*?)</li>', re.DOTALL)
            cards = card_pattern.findall(html)

            count = 0
            for card in cards[:MAX_RESULTS_PER_QUERY]:
                job = _parse_job_card(card)
                if job and job["source_url"] not in seen_urls:
                    seen_urls.add(job["source_url"])
                    results.append(job)
                    count += 1

            logger.info("LinkedIn '%s': %d jobs", query, count)
        except Exception as e:
            logger.error("LinkedIn '%s' error: %s — continuing", query, e)
        finally:
            time.sleep(REQUEST_DELAY)

    return results
