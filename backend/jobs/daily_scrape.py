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
            extracted = extract(title, company, description)
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

            # Build model instance
            job = JobPosting(
                source=posting.get("source", "unknown"),
                source_url=posting["source_url"],
                company=company,
                title=title,
                location=posting.get("location", ""),
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
            )
            db.add(job)
            inserted += 1

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
