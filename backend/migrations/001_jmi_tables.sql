-- Migration 001: Job Market Intelligence tables
-- Run against your PostgreSQL database before deploying the JMI agent.
-- Requires pgvector >= 0.5.0 (for HNSW index support)

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS job_postings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source VARCHAR(50) NOT NULL,
  source_url TEXT UNIQUE NOT NULL,
  company VARCHAR(255) NOT NULL,
  title VARCHAR(255) NOT NULL,
  location VARCHAR(255),
  remote BOOLEAN DEFAULT FALSE,
  description_raw TEXT NOT NULL,
  description_embedding vector(384),
  skills_required JSONB DEFAULT '[]',
  skills_nice_to_have JSONB DEFAULT '[]',
  seniority VARCHAR(50),
  salary_min INTEGER,
  salary_max INTEGER,
  salary_currency VARCHAR(10) DEFAULT 'USD',
  visa_sponsorship BOOLEAN,
  scraped_at TIMESTAMP DEFAULT NOW(),
  posted_at TIMESTAMP,
  role_category VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS idx_job_postings_embedding
  ON job_postings USING hnsw (description_embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_job_postings_scraped_at ON job_postings (scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_job_postings_role_category ON job_postings (role_category);
CREATE INDEX IF NOT EXISTS idx_job_postings_source ON job_postings (source);

CREATE TABLE IF NOT EXISTS skill_trends (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  skill VARCHAR(100) NOT NULL,
  week_start DATE NOT NULL,
  mention_count INTEGER DEFAULT 0,
  role_category VARCHAR(50),
  UNIQUE(skill, week_start, role_category)
);

CREATE INDEX IF NOT EXISTS idx_skill_trends_week ON skill_trends (week_start DESC);
CREATE INDEX IF NOT EXISTS idx_skill_trends_skill ON skill_trends (skill);

CREATE TABLE IF NOT EXISTS weekly_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  week_start DATE NOT NULL UNIQUE,
  report_json JSONB NOT NULL,
  email_sent_at TIMESTAMP,
  total_jobs INTEGER,
  generated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS resume_matches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  resume_hash VARCHAR(64) NOT NULL,
  resume_embedding vector(384),
  top_matches JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
