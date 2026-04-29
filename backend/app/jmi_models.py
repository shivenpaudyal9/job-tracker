"""
SQLAlchemy models for the Job Market Intelligence (JMI) agent.
Separate from core models to keep the existing schema untouched.
"""

import uuid
from sqlalchemy import Column, String, Text, Boolean, Integer, Date, DateTime, JSON, Uuid
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

JMIBase = declarative_base()

try:
    from pgvector.sqlalchemy import Vector
    _VEC384 = Vector(384)
    PGVECTOR_AVAILABLE = True
except ImportError:
    _VEC384 = JSON
    PGVECTOR_AVAILABLE = False


class JobPosting(JMIBase):
    __tablename__ = "job_postings"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String(50), nullable=False, index=True)
    source_url = Column(Text, unique=True, nullable=False)
    company = Column(String(255), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    location = Column(String(255))
    remote = Column(Boolean, default=False)
    description_raw = Column(Text, nullable=False)
    description_embedding = Column(_VEC384, nullable=True)
    skills_required = Column(JSON, default=list)
    skills_nice_to_have = Column(JSON, default=list)
    seniority = Column(String(50))
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    salary_currency = Column(String(10), default="USD")
    visa_sponsorship = Column(Boolean)
    scraped_at = Column(DateTime, server_default=func.now(), index=True)
    posted_at = Column(DateTime)
    role_category = Column(String(50), index=True)
    is_entry_level = Column(Boolean, default=False, index=True)
    city = Column(String(100))
    state = Column(String(50))


class SkillTrend(JMIBase):
    __tablename__ = "skill_trends"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill = Column(String(100), nullable=False, index=True)
    week_start = Column(Date, nullable=False, index=True)
    mention_count = Column(Integer, default=0)
    role_category = Column(String(50))


class WeeklyReport(JMIBase):
    __tablename__ = "weekly_reports"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    week_start = Column(Date, nullable=False, unique=True)
    report_json = Column(JSON, nullable=False)
    email_sent_at = Column(DateTime)
    total_jobs = Column(Integer)
    generated_at = Column(DateTime, server_default=func.now())


class ResumeMatch(JMIBase):
    __tablename__ = "resume_matches"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_hash = Column(String(64), nullable=False, index=True)
    resume_embedding = Column(_VEC384, nullable=True)
    top_matches = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
