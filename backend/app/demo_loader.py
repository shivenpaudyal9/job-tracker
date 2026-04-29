"""
Loads and caches demo_seed.json for fallback when real scraped data is sparse.
All filtering operations run in-process on the cached list.
"""
import json
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)
_cache: Optional[list] = None


def _load() -> list:
    global _cache
    if _cache is not None:
        return _cache
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "demo_seed.json")
    if not os.path.exists(path):
        logger.warning("demo_seed.json not found at %s", path)
        _cache = []
        return _cache
    with open(path, encoding="utf-8") as f:
        _cache = json.load(f)
    logger.info("Loaded %d demo jobs from demo_seed.json", len(_cache))
    return _cache


def get_demo_jobs(
    search: Optional[str] = None,
    role_category: Optional[str] = None,
    seniority: Optional[str] = None,
    remote_only: bool = False,
    visa_only: bool = False,
    entry_level: bool = False,
    city: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> tuple[list, int]:
    jobs = list(_load())

    if search:
        s = search.lower()
        jobs = [
            j for j in jobs
            if s in j.get("company", "").lower()
            or s in j.get("title", "").lower()
            or any(s in sk.lower() for sk in j.get("skills_required", []))
        ]
    if role_category:
        jobs = [j for j in jobs if j.get("role_category") == role_category]
    if seniority:
        jobs = [j for j in jobs if j.get("seniority") == seniority]
    if remote_only:
        jobs = [j for j in jobs if j.get("remote")]
    if visa_only:
        jobs = [j for j in jobs if j.get("visa_sponsorship") is True]
    if entry_level:
        jobs = [j for j in jobs if j.get("is_entry_level") or j.get("seniority") in ("intern", "junior")]
    if city:
        c = city.lower()
        jobs = [j for j in jobs if c in (j.get("city") or j.get("location") or "").lower()]

    total = len(jobs)
    return jobs[offset: offset + limit], total


def total_demo_count() -> int:
    return len(_load())
