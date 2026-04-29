-- Migration 002: Add entry-level and city/state columns to job_postings
-- Safe to run multiple times (uses IF NOT EXISTS / column check idiom)

ALTER TABLE job_postings
  ADD COLUMN IF NOT EXISTS is_entry_level BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS city VARCHAR(100),
  ADD COLUMN IF NOT EXISTS state VARCHAR(50);

CREATE INDEX IF NOT EXISTS idx_job_postings_entry_level ON job_postings (is_entry_level);
CREATE INDEX IF NOT EXISTS idx_job_postings_city ON job_postings (city);
