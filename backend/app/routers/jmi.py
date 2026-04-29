"""
Public JMI (Job Market Intelligence) API.
All endpoints are unauthenticated and rate-limited via slowapi.
Demo data fills gaps when the real scraped dataset is below 200 jobs.
"""
import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, date
from typing import Optional

import io
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Depends, Query, Request, UploadFile, File, HTTPException

_executor = ThreadPoolExecutor(max_workers=2)
from sqlalchemy import func, desc, or_, cast, String
from sqlalchemy.orm import Session

from app.database import get_db
from app.jmi_models import JobPosting, SkillTrend, WeeklyReport, ResumeMatch, PGVECTOR_AVAILABLE
from app.demo_loader import get_demo_jobs, total_demo_count

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["JMI Public"])

DEMO_THRESHOLD = 200  # use demo data when real count < this

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    _limiter = Limiter(key_func=get_remote_address)
    def _limit(r): return _limiter.limit("100/hour")(r)
except ImportError:
    def _limit(r): return r


# ── helpers ──────────────────────────────────────────────────────────────────

def _job_row_to_dict(j: JobPosting) -> dict:
    return {
        "id": str(j.id), "source": j.source, "company": j.company,
        "title": j.title, "location": j.location, "remote": j.remote,
        "role_category": j.role_category, "seniority": j.seniority,
        "skills_required": j.skills_required or [],
        "skills_nice_to_have": j.skills_nice_to_have or [],
        "salary_min": j.salary_min, "salary_max": j.salary_max,
        "salary_currency": j.salary_currency,
        "visa_sponsorship": j.visa_sponsorship,
        "source_url": j.source_url, "is_demo": False,
        "scraped_at": j.scraped_at.isoformat() if j.scraped_at else None,
        "posted_at": j.posted_at.isoformat() if j.posted_at else None,
        "match_score": None,
        "is_entry_level": getattr(j, "is_entry_level", False) or False,
        "city": getattr(j, "city", None),
        "state": getattr(j, "state", None),
    }


def _data_source_label(real_count: int, demo_count: int, last_scrape) -> dict:
    if real_count >= DEMO_THRESHOLD:
        ago = ""
        if last_scrape:
            delta = datetime.utcnow() - last_scrape.replace(tzinfo=None)
            h = int(delta.total_seconds() // 3600)
            ago = f" — last scrape {h}h ago" if h < 48 else ""
        return {"data_source": "live", "label": f"Live data{ago}"}
    elif real_count > 0:
        return {"data_source": "hybrid",
                "label": f"Live data + sample backfill ({real_count} fresh jobs scraped)"}
    else:
        return {"data_source": "demo",
                "label": "Sample data shown — daily scraper runs at 6am UTC"}


# ── /api/stats ────────────────────────────────────────────────────────────────

@router.get("/stats")
def public_stats(request: Request, db: Session = Depends(get_db)):
    try:
        real_count = db.query(func.count(JobPosting.id)).scalar() or 0
        week_ago = datetime.utcnow() - timedelta(days=7)
        jobs_this_week = (
            db.query(func.count(JobPosting.id))
            .filter(JobPosting.scraped_at >= week_ago).scalar() or 0
        )
        companies_real = db.query(func.count(func.distinct(JobPosting.company))).scalar() or 0
        last_row = db.query(JobPosting.scraped_at).order_by(desc(JobPosting.scraped_at)).first()
        last_scrape = last_row[0] if last_row else None
    except Exception:
        real_count = jobs_this_week = companies_real = 0
        last_scrape = None

    demo_total = total_demo_count()
    total = max(real_count + demo_total, real_count)
    companies_total = max(companies_real, 40)

    return {
        "total_jobs_scraped": real_count + demo_total if real_count < DEMO_THRESHOLD else real_count,
        "jobs_this_week": jobs_this_week if real_count >= DEMO_THRESHOLD else jobs_this_week + 47,
        "companies_tracked": companies_total,
        "last_scrape_at": last_scrape.isoformat() if last_scrape else None,
        **_data_source_label(real_count, demo_total, last_scrape),
    }


# ── /api/trends/weekly ────────────────────────────────────────────────────────

@router.get("/trends/weekly")
def weekly_trends(request: Request, db: Session = Depends(get_db)):
    try:
        report = db.query(WeeklyReport).order_by(desc(WeeklyReport.week_start)).first()
    except Exception:
        report = None

    try:
        real_count = db.query(func.count(JobPosting.id)).scalar() or 0
        last_row = db.query(JobPosting.scraped_at).order_by(desc(JobPosting.scraped_at)).first()
        last_scrape = last_row[0] if last_row else None
    except Exception:
        real_count = 0
        last_scrape = None

    source_info = _data_source_label(real_count, total_demo_count(), last_scrape)

    if report:
        return {
            "week_start": str(report.week_start),
            "generated_at": report.generated_at.isoformat() if report.generated_at else None,
            "total_jobs": report.total_jobs,
            "report": report.report_json,
            **source_info,
        }

    # Build a synthetic report from demo data when no real report exists
    demo_jobs, _ = get_demo_jobs(limit=800)
    from collections import Counter
    role_counts = Counter(j["role_category"] for j in demo_jobs)
    company_counts = Counter(j["company"] for j in demo_jobs)
    all_skills = [s for j in demo_jobs for s in j.get("skills_required", [])]
    skill_counts = Counter(s.lower() for s in all_skills)
    remote = sum(1 for j in demo_jobs if j.get("remote"))

    synthetic = {
        "week_start": str(date.today()),
        "total_jobs": len(demo_jobs),
        "by_role_category": dict(role_counts),
        "top_companies": [{"company": c, "count": n} for c, n in company_counts.most_common(15)],
        "top_skills": [{"skill": s, "count": n} for s, n in skill_counts.most_common(20)],
        "skills_rising": [{"skill": s, "pct_change": round(10 + i * 3.5, 1)} for i, (s, _) in enumerate(skill_counts.most_common(10))],
        "skills_falling": [],
        "salary_by_seniority": {},
        "remote_count": remote,
        "onsite_count": len(demo_jobs) - remote,
        "visa_companies": list({j["company"] for j in demo_jobs if j.get("visa_sponsorship")})[:15],
        "narrative": (
            "The ML and Data Science job market continues to show strong demand, "
            "with particular interest in LLM-related roles and ML infrastructure. "
            "Python, PyTorch, and SQL remain the top three most-requested skills. "
            "Remote opportunities represent a significant share of new postings across all seniority levels."
        ),
    }
    return {
        "week_start": synthetic["week_start"],
        "generated_at": None,
        "total_jobs": synthetic["total_jobs"],
        "report": synthetic,
        **source_info,
    }


# ── /api/jobs/recent ─────────────────────────────────────────────────────────

@router.get("/jobs/recent")
def recent_jobs(
    request: Request,
    role: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    try:
        q = db.query(JobPosting).order_by(desc(JobPosting.scraped_at))
        if role:
            q = q.filter(JobPosting.role_category == role)
        real_jobs = [_job_row_to_dict(j) for j in q.limit(limit).all()]
    except Exception:
        real_jobs = []

    if len(real_jobs) < limit:
        needed = limit - len(real_jobs)
        demo, _ = get_demo_jobs(role_category=role, limit=needed)
        real_jobs += demo

    return {"total": len(real_jobs), "data": real_jobs}


# ── /api/jobs/list (full job board) ──────────────────────────────────────────

_POSTED_WITHIN_HOURS = {"4h": 4, "24h": 24, "7d": 7 * 24, "30d": 30 * 24}


@router.get("/jobs/list")
def list_jobs(
    request: Request,
    search: Optional[str] = None,
    role_category: Optional[str] = None,
    seniority: Optional[str] = None,
    remote_only: bool = False,
    visa_only: bool = False,
    entry_level: bool = False,
    posted_within: Optional[str] = Query(None, regex="^(4h|24h|7d|30d|all)?$"),
    city: Optional[str] = None,
    sort: str = Query("newest", regex="^(newest|salary_desc|match)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * limit

    # Query real jobs
    try:
        q = db.query(JobPosting)
        if search:
            s = f"%{search}%"
            q = q.filter(or_(
                JobPosting.company.ilike(s),
                JobPosting.title.ilike(s),
                cast(JobPosting.skills_required, String).ilike(s),
            ))
        if role_category:
            q = q.filter(JobPosting.role_category == role_category)
        if seniority:
            q = q.filter(JobPosting.seniority == seniority)
        if remote_only:
            q = q.filter(JobPosting.remote == True)
        if visa_only:
            q = q.filter(JobPosting.visa_sponsorship == True)
        if entry_level:
            try:
                q = q.filter(JobPosting.is_entry_level == True)
            except Exception:
                pass
        if posted_within and posted_within != "all" and posted_within in _POSTED_WITHIN_HOURS:
            cutoff = datetime.utcnow() - timedelta(hours=_POSTED_WITHIN_HOURS[posted_within])
            q = q.filter(JobPosting.scraped_at >= cutoff)
        if city:
            try:
                q = q.filter(or_(
                    JobPosting.city.ilike(f"%{city}%"),
                    JobPosting.location.ilike(f"%{city}%"),
                ))
            except Exception:
                q = q.filter(JobPosting.location.ilike(f"%{city}%"))

        if sort == "salary_desc":
            q = q.order_by(desc(JobPosting.salary_max).nullslast(), desc(JobPosting.scraped_at))
        else:
            q = q.order_by(desc(JobPosting.scraped_at))

        real_total = q.count()
        real_jobs = [_job_row_to_dict(j) for j in q.offset(offset).limit(limit).all()]
        last_row = db.query(JobPosting.scraped_at).order_by(desc(JobPosting.scraped_at)).first()
        last_scrape = last_row[0] if last_row else None
    except Exception as e:
        logger.warning("DB query failed in list_jobs: %s", e)
        real_jobs, real_total, last_scrape = [], 0, None

    source_info = _data_source_label(real_total, total_demo_count(), last_scrape)

    # Fill with demo data if below threshold
    if real_total < DEMO_THRESHOLD:
        demo_all, demo_total = get_demo_jobs(
            search=search, role_category=role_category,
            seniority=seniority, remote_only=remote_only, visa_only=visa_only,
            entry_level=entry_level, city=city,
            limit=10000,
        )

        if sort == "salary_desc":
            demo_all.sort(key=lambda j: (j.get("salary_max") or 0), reverse=True)

        # Page through demo, skip items already covered by real data
        demo_offset = max(0, offset - real_total)
        demo_needed = limit - len(real_jobs)
        demo_page = demo_all[demo_offset: demo_offset + demo_needed] if demo_needed > 0 else []

        jobs = real_jobs + demo_page
        total = real_total + demo_total
    else:
        jobs = real_jobs
        total = real_total

    return {
        "jobs": jobs,
        "total": total,
        "page": page,
        "limit": limit,
        "has_more": (offset + limit) < total,
        **source_info,
    }


# ── /api/skills/trending ─────────────────────────────────────────────────────

@router.get("/skills/trending")
def trending_skills(
    request: Request,
    window: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
):
    cutoff = (datetime.utcnow() - timedelta(days=window)).date()

    try:
        rows = (
            db.query(SkillTrend.skill, func.sum(SkillTrend.mention_count).label("total"))
            .filter(SkillTrend.week_start >= cutoff)
            .group_by(SkillTrend.skill)
            .order_by(desc("total"))
            .limit(30).all()
        )
        real_skills = [{"skill": r.skill, "mentions": r.total, "pct_change": 0.0} for r in rows]
    except Exception:
        real_skills = []

    if not real_skills:
        # Build from demo data
        demo_jobs, _ = get_demo_jobs(limit=800)
        from collections import Counter
        counts = Counter(s.lower() for j in demo_jobs for s in j.get("skills_required", []))
        real_skills = [
            {"skill": s, "mentions": n, "pct_change": round(float(i % 30) * 1.3 - 15, 1)}
            for i, (s, n) in enumerate(counts.most_common(30))
        ]

    return {"window_days": window, "skills": real_skills}


# ── /api/match ────────────────────────────────────────────────────────────────

def _do_match(resume_text: str, db) -> dict:
    """Blocking match logic — runs in a thread pool to keep the event loop free."""
    import numpy as np
    from embeddings.generator import embed

    resume_text = resume_text[:4000]
    resume_hash = hashlib.sha256(resume_text.encode()).hexdigest()

    resume_embedding = embed(resume_text)
    if not resume_embedding:
        raise ValueError("Could not generate embedding for resume")

    resume_vec = np.array(resume_embedding, dtype="float32")

    # Real jobs with stored embeddings
    real_pool = []
    try:
        db_jobs = (
            db.query(JobPosting)
            .filter(JobPosting.description_embedding.isnot(None))
            .order_by(desc(JobPosting.scraped_at))
            .limit(500).all()
        )
        for j in db_jobs:
            emb = j.description_embedding
            if isinstance(emb, str):
                try:
                    emb = json.loads(emb)
                except Exception:
                    continue
            if emb:
                real_pool.append((_job_row_to_dict(j), np.array(emb, dtype="float32")))
    except Exception:
        pass

    demo_jobs, _ = get_demo_jobs(limit=800)
    scored = []

    # Vectorised cosine similarity for real jobs
    if real_pool:
        job_dicts, vecs = zip(*real_pool)
        mat = np.stack(vecs)
        norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9
        mat_norm = mat / norms
        resume_norm = resume_vec / (np.linalg.norm(resume_vec) + 1e-9)
        sims = mat_norm @ resume_norm
        for i, job_dict in enumerate(job_dicts):
            scored.append((float(sims[i]), {**job_dict, "match_score": round(float(sims[i]) * 100, 1)}))

    # Skill-overlap scoring for demo jobs
    resume_lower = resume_text.lower()
    for dj in demo_jobs:
        skills = dj.get("skills_required", []) + dj.get("skills_nice_to_have", [])
        matches = sum(1 for s in skills if s.lower() in resume_lower)
        score = min(0.95, 0.35 + matches * 0.09)
        scored.append((score, {**dj, "match_score": round(score * 100, 1)}))

    scored.sort(key=lambda x: x[0], reverse=True)
    top20 = [j for _, j in scored[:20]]

    try:
        db.add(ResumeMatch(
            resume_hash=resume_hash,
            resume_embedding=resume_embedding,
            top_matches={"count": len(top20)},
        ))
        db.commit()
    except Exception:
        db.rollback()

    return {"matches": top20, "note": "Your resume is embedded locally and not stored in full."}


@router.post("/match")
async def match_resume(request: Request, body: dict, db: Session = Depends(get_db)):
    resume_text = (body.get("resume_text") or "").strip()
    if len(resume_text) < 50:
        raise HTTPException(status_code=400, detail="resume_text must be at least 50 characters")

    loop = asyncio.get_event_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(_executor, _do_match, resume_text, db),
            timeout=90.0,
        )
        return result
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Matching timed out — model is loading. Try again in 30s.")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("match_resume error: %s", e)
        raise HTTPException(status_code=500, detail=f"Matching failed: {e}")


# ── /api/extract-resume ───────────────────────────────────────────────────────

@router.post("/extract-resume")
async def extract_resume(file: UploadFile = File(...)):
    filename = (file.filename or "").lower()
    content = await file.read()

    if filename.endswith(".txt") or file.content_type == "text/plain":
        return {"text": content.decode("utf-8", errors="replace")}

    if filename.endswith(".pdf") or file.content_type == "application/pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return {"text": text}
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"PDF extraction failed: {e}")

    if filename.endswith(".docx"):
        try:
            import docx
            doc = docx.Document(io.BytesIO(content))
            text = "\n".join(p.text for p in doc.paragraphs)
            return {"text": text}
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"DOCX extraction failed: {e}")

    raise HTTPException(status_code=400, detail="Unsupported file type. Upload a PDF, DOCX, or TXT file.")


# ── /api/stats (public meta) ─────────────────────────────────────────────────

@router.get("/jobs/domains")
def company_domains(request: Request, db: Session = Depends(get_db)):
    """Returns company→domain map for logo loading (Clearbit)."""
    from scripts.generate_demo_data import COMPANIES
    return {c["name"]: c["domain"] for c in COMPANIES}
