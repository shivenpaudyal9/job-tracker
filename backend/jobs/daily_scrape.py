"""
Daily job scrape pipeline. Entry point for the GitHub Actions cron job.
Schedule: 0 6 * * * (6am UTC daily)

Steps:
  1. Run all scrapers
  2. Deduplicate against existing source_urls in DB
  3. For each new posting: LLM extraction + embedding + insert
  4. Update skill_trends table
  5. Log summary
"""

import os
import re
import sys
import logging
from datetime import datetime, date, timedelta, timezone
from collections import defaultdict

# Allow imports from backend/ root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("daily_scrape")

from app.database import SessionLocal
from app.jmi_models import JMIBase, JobPosting, SkillTrend
from app.database import engine

JMIBase.metadata.create_all(bind=engine)

from scrapers.runner import run_all
from llm.extractor import extract
from embeddings.generator import embed

_ENTRY_KEYWORDS = {
    "entry", "junior", "new grad", "new graduate", "intern", "internship",
    "associate", "early career", "early-career", "fresh grad", "0-2 years",
    "0-1 year", "level i ", " i -", "sde i", "sde1", "l1 ", "level 1",
}

_US_STATE_ABBRS = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN",
    "IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV",
    "NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN",
    "TX","UT","VT","VA","WA","WV","WI","WY","DC",
}


def _is_entry_level(title: str, description: str) -> bool:
    text = (title + " " + (description or "")[:300]).lower()
    return any(kw in text for kw in _ENTRY_KEYWORDS)


def _extract_city_state(location: str) -> tuple:
    if not location:
        return None, None
    # "City, ST" pattern
    m = re.match(r"^([^,\(]+),\s*([A-Z]{2})\b", location.strip())
    if m and m.group(2) in _US_STATE_ABBRS:
        return m.group(1).strip(), m.group(2)
    parts = [p.strip() for p in location.split(",")]
    if len(parts) >= 2:
        candidate = parts[1].strip()
        if candidate.upper() in _US_STATE_ABBRS:
            return parts[0].strip(), candidate.upper()
        return parts[0].strip(), None
    return None, None


def _current_week_start() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())  # Monday of current week


def _get_existing_urls(db) -> set[str]:
    rows = db.query(JobPosting.source_url).all()
    return {r[0] for r in rows}


def _upsert_skill_trend(db, skill: str, week_start: date, role_category: str):
    existing = db.query(SkillTrend).filter(
        SkillTrend.skill == skill,
        SkillTrend.week_start == week_start,
        SkillTrend.role_category == role_category,
    ).first()

    if existing:
        existing.mention_count += 1
    else:
        db.add(SkillTrend(
            skill=skill,
            week_start=week_start,
            mention_count=1,
            role_category=role_category,
        ))


def _backfill_extraction(db, limit: int = 300):
    """Re-run LLM extraction for postings saved without it (LLM was down)."""
    pending = (
        db.query(JobPosting)
        .filter(JobPosting.seniority.is_(None), JobPosting.salary_currency == "USD")
        .order_by(JobPosting.scraped_at.desc())
        .limit(limit * 3)
        .all()
    )
    pending = [j for j in pending if not j.skills_required][:limit]
    if not pending:
        return
    logger.info("Backfilling extraction for %d postings", len(pending))
    done = misses = 0
    for job in pending:
        try:
            extracted = extract(job.title, job.company, job.description_raw or "")
        except Exception as e:
            logger.error("Backfill extraction crashed: %s", e)
            extracted = None
        if not extracted:
            misses += 1
            if misses >= 5:
                logger.warning("Backfill stopped: LLM extraction keeps failing")
                break
            continue
        misses = 0
        job.skills_required = extracted.get("skills_required", [])
        job.skills_nice_to_have = extracted.get("skills_nice_to_have", [])
        job.seniority = extracted.get("seniority") or "unknown"
        job.salary_min = extracted.get("salary_min")
        job.salary_max = extracted.get("salary_max")
        job.salary_currency = extracted.get("salary_currency") or "USD"
        job.visa_sponsorship = extracted.get("visa_sponsorship")
        job.role_category = extracted.get("role_category") or job.role_category
        if job.description_embedding is None:
            job.description_embedding = embed(job.description_raw or "")
        done += 1
        if done % 20 == 0:
            db.commit()
    db.commit()
    logger.info("Backfill complete: %d postings updated", done)


def run():
    logger.info("=== Daily scrape started ===")
    db = SessionLocal()

    try:
        # 1. Scrape
        raw_postings = run_all()
        logger.info("Scraped %d raw postings", len(raw_postings))

        # 2. Deduplicate
        existing_urls = _get_existing_urls(db)
        new_postings = [p for p in raw_postings if p.get("source_url") and p["source_url"] not in existing_urls]
        logger.info("%d new postings after dedup (skipped %d)", len(new_postings), len(raw_postings) - len(new_postings))

        week_start = _current_week_start()
        inserted = 0
        failed_extraction = 0
        skill_counter = defaultdict(lambda: defaultdict(int))

        # 3. Process each new posting
        for posting in new_postings:
            title = posting.get("title", "")
            company = posting.get("company", "")
            description = posting.get("description_raw", "")

            # LLM extraction
            try:
                extracted = extract(title, company, description)
            except Exception as e:
                logger.error("Extraction crashed for '%s': %s", title, e)
                extracted = None
            if not extracted:
                failed_extraction += 1
                # Still insert with minimal data
                extracted = {
                    "skills_required": [],
                    "skills_nice_to_have": [],
                    "seniority": None,
                    "salary_min": None,
                    "salary_max": None,
                    "salary_currency": "USD",
                    "visa_sponsorship": None,
                    "role_category": "ml_engineer",
                }

            # Embedding
            embedding = embed(description)

            # Derive entry-level and city/state
            location_str = posting.get("location", "")
            entry_level = _is_entry_level(title, description)
            city, state = _extract_city_state(location_str)

            # Build model instance
            job = JobPosting(
                source=posting.get("source", "unknown"),
                source_url=posting["source_url"],
                company=company,
                title=title,
                location=location_str,
                remote=posting.get("remote", False),
                description_raw=description,
                description_embedding=embedding,
                skills_required=extracted.get("skills_required", []),
                skills_nice_to_have=extracted.get("skills_nice_to_have", []),
                seniority=extracted.get("seniority"),
                salary_min=extracted.get("salary_min"),
                salary_max=extracted.get("salary_max"),
                salary_currency=extracted.get("salary_currency", "USD"),
                visa_sponsorship=extracted.get("visa_sponsorship"),
                role_category=extracted.get("role_category", "ml_engineer"),
                posted_at=_parse_date(posting.get("posted_at")),
                is_entry_level=entry_level,
                city=city,
                state=state,
            )
            db.add(job)
            inserted += 1
            # Commit in batches so an interrupted run keeps its progress.
            if inserted % 20 == 0:
                db.commit()
                logger.info("Committed %d/%d new postings", inserted, len(new_postings))

            # Track skills for trend update
            role_cat = extracted.get("role_category", "ml_engineer")
            for skill in extracted.get("skills_required", []):
                skill_counter[skill.lower()][role_cat] += 1

        db.flush()

        # 4. Update skill_trends
        for skill, role_counts in skill_counter.items():
            for role_cat, count in role_counts.items():
                existing = db.query(SkillTrend).filter(
                    SkillTrend.skill == skill,
                    SkillTrend.week_start == week_start,
                    SkillTrend.role_category == role_cat,
                ).first()
                if existing:
                    existing.mention_count += count
                else:
                    db.add(SkillTrend(
                        skill=skill,
                        week_start=week_start,
                        mention_count=count,
                        role_category=role_cat,
                    ))

        db.commit()

        # 5. Fill in postings that were saved while the LLM was unavailable
        try:
            _backfill_extraction(db)
        except Exception as e:
            db.rollback()
            logger.error("Backfill failed: %s", e)

        logger.info(
            "=== Daily scrape complete: %d scraped, %d new inserted, %d failed extraction ===",
            len(raw_postings), inserted, failed_extraction,
        )

    except Exception as e:
        db.rollback()
        logger.exception("Daily scrape failed: %s", e)
        raise
    finally:
        db.close()


def _parse_date(val):
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        from dateutil import parser as dp
        return dp.parse(str(val))
    except Exception:
        return None


if __name__ == "__main__":
    run()
