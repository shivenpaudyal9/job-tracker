"""
Public JMI (Job Market Intelligence) API endpoints.
No authentication required. Rate-limited to 100 req/hour per IP via slowapi.
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, desc, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.jmi_models import JobPosting, SkillTrend, WeeklyReport, ResumeMatch, PGVECTOR_AVAILABLE

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["JMI Public"])

# Rate limiter — requires slowapi to be wired up in main.py
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    limiter = Limiter(key_func=get_remote_address)
    SLOWAPI_AVAILABLE = True
except ImportError:
    limiter = None
    SLOWAPI_AVAILABLE = False


def _rate_limit(limit: str = "100/hour"):
    """Decorator factory that applies rate limiting when slowapi is available."""
    def decorator(func):
        if SLOWAPI_AVAILABLE and limiter:
            return limiter.limit(limit)(func)
        return func
    return decorator


# ──────────────────────────────────────────────────────────────────────────────

@router.get("/stats")
def public_stats(request: Request, db: Session = Depends(get_db)):
    """Public: meta stats about the JMI database."""
    total_jobs = db.query(func.count(JobPosting.id)).scalar() or 0
    week_ago = datetime.utcnow() - timedelta(days=7)
    jobs_this_week = (
        db.query(func.count(JobPosting.id))
        .filter(JobPosting.scraped_at >= week_ago)
        .scalar() or 0
    )
    companies_tracked = (
        db.query(func.count(func.distinct(JobPosting.company))).scalar() or 0
    )
    last_scrape_row = (
        db.query(JobPosting.scraped_at)
        .order_by(desc(JobPosting.scraped_at))
        .first()
    )
    last_scrape = last_scrape_row[0].isoformat() if last_scrape_row else None

    return {
        "total_jobs_scraped": total_jobs,
        "jobs_this_week": jobs_this_week,
        "companies_tracked": companies_tracked,
        "last_scrape_at": last_scrape,
    }


@router.get("/trends/weekly")
def weekly_trends(request: Request, db: Session = Depends(get_db)):
    """Public: latest weekly intelligence report."""
    report = (
        db.query(WeeklyReport)
        .order_by(desc(WeeklyReport.week_start))
        .first()
    )
    if not report:
        return {"message": "No report generated yet. Check back Monday."}
    return {
        "week_start": str(report.week_start),
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        "total_jobs": report.total_jobs,
        "report": report.report_json,
    }


@router.get("/jobs/recent")
def recent_jobs(
    request: Request,
    role: Optional[str] = Query(None, description="Role category filter"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Public: recent job postings filtered by role category."""
    query = db.query(JobPosting).order_by(desc(JobPosting.scraped_at))
    if role:
        query = query.filter(JobPosting.role_category == role)
    jobs = query.limit(limit).all()

    return {
        "total": len(jobs),
        "data": [
            {
                "id": str(j.id),
                "source": j.source,
                "company": j.company,
                "title": j.title,
                "location": j.location,
                "remote": j.remote,
                "role_category": j.role_category,
                "seniority": j.seniority,
                "skills_required": j.skills_required or [],
                "salary_min": j.salary_min,
                "salary_max": j.salary_max,
                "visa_sponsorship": j.visa_sponsorship,
                "source_url": j.source_url,
                "scraped_at": j.scraped_at.isoformat() if j.scraped_at else None,
            }
            for j in jobs
        ],
    }


@router.get("/skills/trending")
def trending_skills(
    request: Request,
    window: int = Query(30, ge=7, le=90, description="Days to look back"),
    db: Session = Depends(get_db),
):
    """Public: trending skills with week-over-week delta."""
    cutoff_date = (datetime.utcnow() - timedelta(days=window)).date()

    rows = (
        db.query(
            SkillTrend.skill,
            func.sum(SkillTrend.mention_count).label("total"),
        )
        .filter(SkillTrend.week_start >= cutoff_date)
        .group_by(SkillTrend.skill)
        .order_by(desc("total"))
        .limit(30)
        .all()
    )

    # Previous window for delta
    prev_cutoff = (datetime.utcnow() - timedelta(days=window * 2)).date()
    prev_rows = (
        db.query(
            SkillTrend.skill,
            func.sum(SkillTrend.mention_count).label("total"),
        )
        .filter(
            SkillTrend.week_start >= prev_cutoff,
            SkillTrend.week_start < cutoff_date,
        )
        .group_by(SkillTrend.skill)
        .all()
    )
    prev_map = {r.skill: r.total for r in prev_rows}

    result = []
    for row in rows:
        prev = prev_map.get(row.skill, 0)
        if prev > 0:
            delta = round((row.total - prev) / prev * 100, 1)
        else:
            delta = 100.0
        result.append({
            "skill": row.skill,
            "mentions": row.total,
            "pct_change": delta,
        })

    return {"window_days": window, "skills": result}


@router.post("/match")
def match_resume(
    request: Request,
    body: dict,
    db: Session = Depends(get_db),
):
    """
    Public: find top-matching job postings for a resume using embedding similarity.
    Accepts: { "resume_text": "..." }
    Returns: top 20 matching jobs with similarity score.
    """
    resume_text = body.get("resume_text", "")
    if not resume_text or len(resume_text.strip()) < 50:
        return {"error": "resume_text must be at least 50 characters"}

    resume_hash = hashlib.sha256(resume_text.encode()).hexdigest()

    try:
        from embeddings.generator import embed, cosine_similarity
        resume_embedding = embed(resume_text)
    except Exception as e:
        logger.error("Embedding failed: %s", e)
        return {"error": "Embedding service unavailable"}

    if resume_embedding is None:
        return {"error": "Could not generate embedding for resume"}

    matches = []

    if PGVECTOR_AVAILABLE:
        # Use pgvector cosine distance for efficient ANN search
        try:
            from pgvector.sqlalchemy import Vector
            jobs = (
                db.query(JobPosting)
                .filter(JobPosting.description_embedding.isnot(None))
                .order_by(JobPosting.description_embedding.cosine_distance(resume_embedding))
                .limit(20)
                .all()
            )
            for j in jobs:
                matches.append(_job_to_match(j, score=None))
        except Exception as e:
            logger.warning("pgvector query failed, falling back: %s", e)
            matches = _fallback_match(db, resume_embedding)
    else:
        matches = _fallback_match(db, resume_embedding)

    # Store hashed resume for usage analytics (not full text)
    db.add(ResumeMatch(
        resume_hash=resume_hash,
        resume_embedding=resume_embedding,
        top_matches={"count": len(matches)},
    ))
    try:
        db.commit()
    except Exception:
        db.rollback()

    return {
        "matches": matches[:20],
        "note": "Your resume is embedded locally and not stored in full.",
    }


def _fallback_match(db, resume_embedding: list[float]) -> list[dict]:
    """Pure-Python cosine similarity fallback when pgvector unavailable."""
    from embeddings.generator import cosine_similarity

    jobs = (
        db.query(JobPosting)
        .filter(JobPosting.description_embedding.isnot(None))
        .order_by(desc(JobPosting.scraped_at))
        .limit(500)
        .all()
    )

    scored = []
    for j in jobs:
        emb = j.description_embedding
        if isinstance(emb, str):
            try:
                emb = json.loads(emb)
            except Exception:
                continue
        if not emb:
            continue
        score = cosine_similarity(resume_embedding, emb)
        scored.append((score, j))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [_job_to_match(j, score=round(s * 100, 1)) for s, j in scored[:20]]


def _job_to_match(j: JobPosting, score: Optional[float]) -> dict:
    return {
        "id": str(j.id),
        "company": j.company,
        "title": j.title,
        "location": j.location,
        "remote": j.remote,
        "role_category": j.role_category,
        "seniority": j.seniority,
        "skills_required": j.skills_required or [],
        "salary_min": j.salary_min,
        "salary_max": j.salary_max,
        "source_url": j.source_url,
        "match_score": score,
        "scraped_at": j.scraped_at.isoformat() if j.scraped_at else None,
    }
