"""
Database models for Job Tracker

Schema design principles:
- RawEmail: immutable source of truth
- Application: one row per unique job application
- ApplicationEvent: timeline of status changes
- Link: extracted URLs with types
- ManualReview: queue for low-confidence items
- Company: optional normalization table
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float,
    ForeignKey, Index, JSON, Enum as SQLEnum, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum
from typing import Optional

# Import Base from database module to ensure all models use the same Base
from app.database import Base


# Enums
class ApplicationStatus(str, Enum):
    """Normalized application status/stage"""
    APPLIED_RECEIVED = "APPLIED_RECEIVED"  # Application submitted and confirmed
    IN_REVIEW = "IN_REVIEW"  # Under review by recruiter/team
    NEXT_STEP_ASSESSMENT = "NEXT_STEP_ASSESSMENT"  # Coding challenge, take-home assignment
    NEXT_STEP_SCHEDULING = "NEXT_STEP_SCHEDULING"  # Need to schedule interview
    INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED"  # Interview date confirmed
    INTERVIEW_COMPLETED = "INTERVIEW_COMPLETED"  # Interview done, awaiting decision
    OFFER_EXTENDED = "OFFER_EXTENDED"  # Offer received
    OFFER_ACCEPTED = "OFFER_ACCEPTED"  # Accepted offer
    REJECTED = "REJECTED"  # Application rejected
    WITHDRAWN = "WITHDRAWN"  # Withdrew application
    GHOSTED = "GHOSTED"  # No response after follow-up
    OTHER_UPDATE = "OTHER_UPDATE"  # General update


class ActionType(str, Enum):
    """Types of actions user needs to take"""
    COMPLETE_ASSESSMENT = "COMPLETE_ASSESSMENT"  # Complete coding challenge
    SCHEDULE_INTERVIEW = "SCHEDULE_INTERVIEW"  # Pick interview slot
    RESPOND_TO_EMAIL = "RESPOND_TO_EMAIL"  # Recruiter waiting for response
    SUBMIT_DOCUMENTS = "SUBMIT_DOCUMENTS"  # Upload documents
    FOLLOW_UP = "FOLLOW_UP"  # Time to send follow-up
    ACCEPT_OFFER = "ACCEPT_OFFER"  # Decision needed on offer
    OTHER = "OTHER"


class LinkType(str, Enum):
    """Types of extracted links"""
    JOB_POSTING = "JOB_POSTING"  # Original job listing
    ASSESSMENT_PORTAL = "ASSESSMENT_PORTAL"  # HackerRank, CodeSignal, etc.
    SCHEDULING_LINK = "SCHEDULING_LINK"  # Calendly, Google Calendar, etc.
    VIDEO_INTERVIEW = "VIDEO_INTERVIEW"  # Zoom, Teams link
    COMPANY_PORTAL = "COMPANY_PORTAL"  # ATS portal (Workday, Greenhouse)
    DOCUMENT_UPLOAD = "DOCUMENT_UPLOAD"  # Upload forms, references
    OTHER = "OTHER"


class EmailType(str, Enum):
    """Classification of email type"""
    APPLICATION_CONFIRMATION = "APPLICATION_CONFIRMATION"
    REJECTION = "REJECTION"
    ASSESSMENT_INVITE = "ASSESSMENT_INVITE"
    INTERVIEW_REQUEST = "INTERVIEW_REQUEST"
    INTERVIEW_CONFIRMATION = "INTERVIEW_CONFIRMATION"
    OFFER = "OFFER"
    GENERAL_UPDATE = "GENERAL_UPDATE"
    UNKNOWN = "UNKNOWN"


# Models

class User(Base):
    """
    User account for multi-user support
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(255))

    # Outlook connection per user
    is_outlook_connected = Column(Boolean, default=False, nullable=False)
    outlook_token_cache = Column(Text)  # Encrypted token cache per user
    outlook_email = Column(String(255))  # User's Outlook email

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))

    # Relationships
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")
    raw_emails = relationship("RawEmail", back_populates="user", cascade="all, delete-orphan")
    manual_reviews = relationship("ManualReview", back_populates="user", cascade="all, delete-orphan")
    sync_states = relationship("SyncState", back_populates="user", cascade="all, delete-orphan")


class RawEmail(Base):
    """
    Immutable storage of raw emails from Outlook.
    Source of truth - never delete or modify after creation.
    """
    __tablename__ = "raw_emails"

    id = Column(Integer, primary_key=True, index=True)

    # User ownership
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Outlook identifiers
    outlook_message_id = Column(String(500), unique=True, nullable=False, index=True)
    outlook_conversation_id = Column(String(500), index=True)  # Threading (may be broken by forwarding)

    # Outlook metadata
    received_datetime = Column(DateTime(timezone=True), nullable=False, index=True)
    outlook_from = Column(String(500))  # May be Gmail forwarding address
    outlook_to = Column(String(500))
    outlook_subject = Column(Text)

    # Raw content
    body_html = Column(Text)  # Original HTML body
    body_text = Column(Text)  # Plain text version
    raw_headers = Column(JSON)  # All email headers as JSON

    # Unwrapped/extracted fields (populated by unwrapper)
    original_from = Column(String(500), index=True)  # Extracted from forward
    original_subject = Column(Text, index=True)
    original_sent_date = Column(DateTime(timezone=True), index=True)
    original_to = Column(String(500))
    clean_body_text = Column(Text)  # Unwrapped, cleaned body
    clean_body_html = Column(Text)
    unwrap_confidence = Column(Float)  # 0.0-1.0

    # Classification results (populated by classifier)
    email_type = Column(SQLEnum(EmailType))
    extracted_data = Column(JSON)  # Full extraction results as JSON
    email_fingerprint = Column(String(64), unique=True, index=True)  # SHA256 hash for dedupe
    overall_confidence = Column(Float, index=True)  # 0.0-1.0
    parser_version = Column(String(50))  # Version of parser used

    # Processing metadata
    processed = Column(Boolean, default=False, nullable=False, index=True)
    processing_error = Column(Text)  # Error message if processing failed
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="raw_emails")
    events = relationship("ApplicationEvent", back_populates="raw_email")
    manual_reviews = relationship("ManualReview", back_populates="raw_email", foreign_keys="[ManualReview.raw_email_id]")

    __table_args__ = (
        Index('idx_raw_emails_received_processed', 'received_datetime', 'processed'),
        Index('idx_raw_emails_fingerprint_unique', 'email_fingerprint'),
        Index('idx_raw_emails_user', 'user_id'),
    )


class Application(Base):
    """
    Canonical representation of a job application.
    One row per unique company + job_title combination per user.
    """
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)

    # User ownership
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Core fields (extracted from emails)
    company_name = Column(String(500), nullable=False, index=True)
    job_title = Column(String(500), nullable=False, index=True)
    location = Column(String(500))  # Remote / City, State / etc.

    # Application metadata
    application_date = Column(DateTime(timezone=True), index=True)  # When user applied
    first_seen_date = Column(DateTime(timezone=True), nullable=False)  # When first email received

    # Current status
    current_status = Column(SQLEnum(ApplicationStatus), nullable=False, index=True)
    status_updated_at = Column(DateTime(timezone=True), nullable=False)

    # Action tracking
    action_required = Column(Boolean, default=False, nullable=False, index=True)
    action_type = Column(SQLEnum(ActionType))
    action_deadline = Column(DateTime(timezone=True), index=True)
    action_description = Column(Text)

    # Confidence and data quality
    company_confidence = Column(Float)  # 0.0-1.0
    job_title_confidence = Column(Float)
    overall_confidence = Column(Float, index=True)

    # Denormalized fields for performance
    latest_email_date = Column(DateTime(timezone=True))
    event_count = Column(Integer, default=0)
    link_count = Column(Integer, default=0)

    # User notes and archival
    notes = Column(Text)  # User's personal notes
    is_archived = Column(Boolean, default=False, nullable=False, index=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Optional company normalization
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)

    # Relationships
    user = relationship("User", back_populates="applications")
    events = relationship("ApplicationEvent", back_populates="application", cascade="all, delete-orphan")
    links = relationship("Link", back_populates="application", cascade="all, delete-orphan")
    company = relationship("Company", back_populates="applications")
    manual_reviews = relationship("ManualReview", back_populates="application", foreign_keys="[ManualReview.application_id]")

    __table_args__ = (
        UniqueConstraint('user_id', 'company_name', 'job_title', name='uq_user_application_company_title'),
        Index('idx_applications_status_action', 'current_status', 'action_required'),
        Index('idx_applications_company_confidence', 'company_name', 'overall_confidence'),
        Index('idx_applications_user', 'user_id'),
    )


class ApplicationEvent(Base):
    """
    Timeline of all status changes and updates for an application.
    Many events per application - creates audit trail.
    """
    __tablename__ = "application_events"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    raw_email_id = Column(Integer, ForeignKey("raw_emails.id"), index=True)  # Source email

    # Event data
    event_type = Column(SQLEnum(EmailType), nullable=False)
    status = Column(SQLEnum(ApplicationStatus), nullable=False, index=True)
    event_date = Column(DateTime(timezone=True), nullable=False, index=True)

    # Event details
    title = Column(String(500))  # Human-readable title
    description = Column(Text)  # Full description/notes
    extracted_data = Column(JSON)  # Raw extracted data from email

    # Metadata
    confidence = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    application = relationship("Application", back_populates="events")
    raw_email = relationship("RawEmail", back_populates="events")

    __table_args__ = (
        Index('idx_events_application_date', 'application_id', 'event_date'),
        Index('idx_events_status_date', 'status', 'event_date'),
    )


class Link(Base):
    """
    Extracted links from emails (assessment portals, scheduling, etc.)
    """
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    raw_email_id = Column(Integer, ForeignKey("raw_emails.id"), index=True)

    # Link data
    url = Column(Text, nullable=False)
    link_type = Column(SQLEnum(LinkType), nullable=False, index=True)
    link_text = Column(Text)  # Anchor text or surrounding context

    # Metadata
    confidence = Column(Float)
    expires_at = Column(DateTime(timezone=True))  # If deadline/expiry detected
    clicked = Column(Boolean, default=False)  # Track if user visited
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    application = relationship("Application", back_populates="links")

    __table_args__ = (
        Index('idx_links_application_type', 'application_id', 'link_type'),
    )


class Company(Base):
    """
    Optional: normalized company table for deduplication and enrichment.
    """
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)

    # Company data
    name = Column(String(500), unique=True, nullable=False, index=True)
    normalized_name = Column(String(500), index=True)  # Lowercase, stripped
    domain = Column(String(500), index=True)  # company.com

    # Enrichment (optional - from external APIs)
    industry = Column(String(200))
    size_range = Column(String(50))  # "51-200", "1001-5000"
    location = Column(String(500))

    # Metadata
    application_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    applications = relationship("Application", back_populates="company")


class ManualReview(Base):
    """
    Queue for low-confidence items requiring human review.
    """
    __tablename__ = "manual_reviews"

    id = Column(Integer, primary_key=True, index=True)

    # User ownership
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Foreign keys
    raw_email_id = Column(Integer, ForeignKey("raw_emails.id"), nullable=False, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), index=True)  # Null if no match

    # Review data
    reason = Column(String(500), nullable=False)  # Why flagged for review
    suggested_company = Column(String(500))
    suggested_job_title = Column(String(500))
    suggested_status = Column(SQLEnum(ApplicationStatus))
    confidence = Column(Float)

    # Review status
    reviewed = Column(Boolean, default=False, nullable=False, index=True)
    reviewed_at = Column(DateTime(timezone=True))
    reviewed_by = Column(String(200))  # User who reviewed (if multi-user)

    # User decisions
    user_company = Column(String(500))  # User-confirmed company
    user_job_title = Column(String(500))
    user_status = Column(SQLEnum(ApplicationStatus))
    user_notes = Column(Text)

    # Action taken
    action_taken = Column(String(100))  # "created_new", "linked_to_existing", "ignored"
    created_application_id = Column(Integer, ForeignKey("applications.id"))  # If new app created

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="manual_reviews")
    raw_email = relationship("RawEmail", back_populates="manual_reviews", foreign_keys=[raw_email_id])
    application = relationship("Application", back_populates="manual_reviews", foreign_keys=[application_id])

    __table_args__ = (
        Index('idx_manual_review_status', 'reviewed', 'created_at'),
        Index('idx_manual_review_user', 'user_id'),
    )


class ExportLog(Base):
    """
    Track Excel exports for reproducibility and auditing.
    """
    __tablename__ = "export_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Export metadata
    export_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    file_path = Column(String(1000))
    file_size_bytes = Column(Integer)

    # Export scope
    applications_count = Column(Integer)
    events_count = Column(Integer)
    actions_count = Column(Integer)

    # Filters applied (if any)
    filters_applied = Column(JSON)

    # Metadata
    duration_seconds = Column(Float)
    success = Column(Boolean, default=True)
    error_message = Column(Text)


# Database initialization function
def create_tables(engine):
    """Create all tables in the database"""
    Base.metadata.create_all(bind=engine)


def drop_tables(engine):
    """Drop all tables (use with caution!)"""
    Base.metadata.drop_all(bind=engine)


class SyncState(Base):
    """Track sync state and history per user"""
    __tablename__ = "sync_state"

    id = Column(Integer, primary_key=True, index=True)

    # User ownership
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Sync metadata
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    is_running = Column(Boolean, default=False, nullable=False)
    
    # Results
    emails_fetched = Column(Integer, default=0)
    emails_processed = Column(Integer, default=0)
    applications_created = Column(Integer, default=0)
    applications_updated = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    error_message = Column(Text)
    
    # Auth state
    is_connected = Column(Boolean, default=False)
    last_token_refresh = Column(DateTime(timezone=True))

    success = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="sync_states")
