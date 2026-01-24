"""
FastAPI REST API for Job Tracker - Enhanced Version

Endpoints:
- GET /health - Health check
- GET /applications - List applications with filters
- GET /applications/{id} - Get single application with events
- GET /applications/{id}/events - Get application events
- POST /applications - Create application manually
- PATCH /applications/{id} - Update application
- DELETE /applications/{id} - Delete application

- GET /manual-reviews - List items needing review
- POST /manual-reviews/{id}/resolve - Resolve manual review

- GET /sync/health - Sync health check
- GET /sync/status - Get sync status
- POST /sync/connect/start - Start device code flow
- POST /sync/connect/poll - Poll for auth completion
- POST /sync/run - Trigger sync
- GET /sync/export/excel - Export to Excel

- GET /stats - Dashboard statistics
"""

from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timezone
import logging
import os

from app.database import get_db, engine
from app.models import (
    Base, Application, ApplicationEvent, ManualReview, Link, User,
    ApplicationStatus, ActionType, SyncState
)
from app.routers import sync, auth
from app.auth import get_current_user

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI
app = FastAPI(
    title="Job Tracker API",
    description="Production job application tracking system with Outlook sync",
    version="2.0.0"
)

# CORS - Allow frontend origins
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)


# Pydantic schemas
from pydantic import BaseModel

class ApplicationCreate(BaseModel):
    company_name: str
    job_title: str
    location: Optional[str] = None
    application_date: Optional[datetime] = None
    current_status: ApplicationStatus = ApplicationStatus.APPLIED_RECEIVED

class ApplicationUpdate(BaseModel):
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    location: Optional[str] = None
    current_status: Optional[ApplicationStatus] = None
    action_required: Optional[bool] = None
    action_type: Optional[ActionType] = None
    action_deadline: Optional[datetime] = None
    action_description: Optional[str] = None
    notes: Optional[str] = None
    is_archived: Optional[bool] = None

class ManualReviewResolve(BaseModel):
    action: str  # "create_new", "link_to_existing", "ignore"
    application_id: Optional[int] = None
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    location: Optional[str] = None
    current_status: Optional[ApplicationStatus] = None


# Include routers
app.include_router(auth.router)
app.include_router(sync.router)


# Root endpoints

@app.get("/")
def root():
    """API health check"""
    return {
        "status": "ok",
        "service": "Job Tracker API",
        "version": "2.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "connected"
    }


# Application endpoints

@app.get("/applications")
def list_applications(
    search: Optional[str] = None,
    status: Optional[ApplicationStatus] = None,
    company: Optional[str] = None,
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    action_required: Optional[bool] = None,
    is_archived: Optional[bool] = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List applications with filters (user-scoped)

    Query params:
    - search: Search in company name or job title
    - status: Filter by application status
    - company: Filter by company name (partial match)
    - min_confidence: Minimum confidence score (0.0-1.0)
    - action_required: Filter by action required flag
    - is_archived: Filter by archived status (default: False)
    - skip: Pagination offset
    - limit: Pagination limit
    """
    query = db.query(Application).filter(Application.user_id == current_user.id)

    # Filter by archived status
    if is_archived is not None:
        query = query.filter(Application.is_archived == is_archived)

    # Apply filters
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Application.company_name.ilike(search_filter)) |
            (Application.job_title.ilike(search_filter))
        )

    if status:
        query = query.filter(Application.current_status == status)

    if company:
        query = query.filter(Application.company_name.ilike(f"%{company}%"))

    if min_confidence is not None:
        query = query.filter(Application.overall_confidence >= min_confidence)

    if action_required is not None:
        query = query.filter(Application.action_required == action_required)

    # Get total count
    total = query.count()

    # Get paginated results
    applications = query.order_by(desc(Application.first_seen_date)).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": [
            {
                "id": app.id,
                "company_name": app.company_name,
                "job_title": app.job_title,
                "location": app.location,
                "current_status": app.current_status,
                "application_date": app.application_date,
                "first_seen_date": app.first_seen_date,
                "status_updated_at": app.status_updated_at,
                "action_required": app.action_required,
                "action_type": app.action_type,
                "action_deadline": app.action_deadline,
                "action_description": app.action_description,
                "overall_confidence": app.overall_confidence,
                "company_confidence": app.company_confidence,
                "job_title_confidence": app.job_title_confidence,
                "event_count": app.event_count,
                "link_count": app.link_count,
                "notes": app.notes,
                "is_archived": app.is_archived,
                "created_at": app.created_at,
                "updated_at": app.updated_at
            }
            for app in applications
        ]
    }


@app.get("/applications/{application_id}")
def get_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get single application with all details (user-scoped)"""
    app = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    return {
        "id": app.id,
        "company_name": app.company_name,
        "job_title": app.job_title,
        "location": app.location,
        "current_status": app.current_status,
        "application_date": app.application_date,
        "first_seen_date": app.first_seen_date,
        "status_updated_at": app.status_updated_at,
        "action_required": app.action_required,
        "action_type": app.action_type,
        "action_deadline": app.action_deadline,
        "action_description": app.action_description,
        "overall_confidence": app.overall_confidence,
        "company_confidence": app.company_confidence,
        "job_title_confidence": app.job_title_confidence,
        "event_count": app.event_count,
        "link_count": app.link_count,
        "notes": app.notes,
        "is_archived": app.is_archived,
        "created_at": app.created_at,
        "updated_at": app.updated_at,
        "events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "event_date": event.event_date,
                "status": event.status,
                "title": event.title,
                "description": event.description,
                "confidence": event.confidence,
                "created_at": event.created_at
            }
            for event in app.events
        ],
        "links": [
            {
                "id": link.id,
                "url": link.url,
                "link_type": link.link_type,
                "link_text": link.link_text,
                "confidence": link.confidence,
                "created_at": link.created_at
            }
            for link in app.links
        ]
    }


@app.get("/applications/{application_id}/events")
def get_application_events(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get events for a specific application (user-scoped)"""
    app = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    events = db.query(ApplicationEvent).filter(
        ApplicationEvent.application_id == application_id
    ).order_by(desc(ApplicationEvent.event_date)).all()

    return {
        "application_id": application_id,
        "total": len(events),
        "events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "event_date": event.event_date,
                "status": event.status,
                "title": event.title,
                "description": event.description,
                "confidence": event.confidence,
                "created_at": event.created_at
            }
            for event in events
        ]
    }


@app.post("/applications", status_code=201)
def create_application(
    data: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new application manually (user-scoped)"""
    app = Application(
        user_id=current_user.id,
        company_name=data.company_name,
        job_title=data.job_title,
        location=data.location,
        application_date=data.application_date or datetime.now(timezone.utc),
        first_seen_date=datetime.now(timezone.utc),
        current_status=data.current_status,
        status_updated_at=datetime.now(timezone.utc),
        overall_confidence=1.0,  # Manual entry = high confidence
        company_confidence=1.0,
        job_title_confidence=1.0
    )

    db.add(app)
    db.commit()
    db.refresh(app)

    return {
        "id": app.id,
        "company_name": app.company_name,
        "job_title": app.job_title,
        "message": "Application created successfully"
    }


@app.patch("/applications/{application_id}")
def update_application(
    application_id: int,
    data: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update application (user-scoped)"""
    app = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Track status change
    old_status = app.current_status

    # Update fields
    if data.company_name is not None:
        app.company_name = data.company_name

    if data.job_title is not None:
        app.job_title = data.job_title

    if data.location is not None:
        app.location = data.location

    if data.current_status is not None and data.current_status != old_status:
        app.current_status = data.current_status
        app.status_updated_at = datetime.now(timezone.utc)

    if data.action_required is not None:
        app.action_required = data.action_required

    if data.action_type is not None:
        app.action_type = data.action_type

    if data.action_deadline is not None:
        app.action_deadline = data.action_deadline

    if data.action_description is not None:
        app.action_description = data.action_description

    if data.notes is not None:
        app.notes = data.notes

    if data.is_archived is not None:
        app.is_archived = data.is_archived

    app.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(app)

    return {
        "id": app.id,
        "message": "Application updated successfully",
        "updated_fields": data.dict(exclude_none=True)
    }


@app.delete("/applications/{application_id}")
def delete_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete application (user-scoped)"""
    app = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    company = app.company_name
    title = app.job_title

    db.delete(app)
    db.commit()

    return {
        "message": "Application deleted successfully",
        "company": company,
        "job_title": title
    }


# Manual Review endpoints

@app.get("/manual-reviews")
def list_manual_reviews(
    reviewed: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List items in manual review queue (user-scoped)"""
    query = db.query(ManualReview).filter(
        ManualReview.reviewed == reviewed,
        ManualReview.user_id == current_user.id
    )

    total = query.count()
    items = query.order_by(desc(ManualReview.created_at)).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": [
            {
                "id": item.id,
                "reason": item.reason,
                "confidence": item.confidence,
                "suggested_company": item.suggested_company,
                "suggested_job_title": item.suggested_job_title,
                "suggested_status": item.suggested_status,
                "reviewed": item.reviewed,
                "created_at": item.created_at,
                "raw_email": {
                    "id": item.raw_email.id,
                    "subject": item.raw_email.outlook_subject,
                    "from": item.raw_email.outlook_from,
                    "received": item.raw_email.received_datetime,
                    "body_preview": item.raw_email.body_text[:500] if item.raw_email.body_text else None
                } if item.raw_email else None
            }
            for item in items
        ]
    }


@app.post("/manual-reviews/{review_id}/resolve")
def resolve_manual_review(
    review_id: int,
    data: ManualReviewResolve,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resolve a manual review item (user-scoped)"""
    review = db.query(ManualReview).filter(
        ManualReview.id == review_id,
        ManualReview.user_id == current_user.id
    ).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.reviewed = True
    review.reviewed_at = datetime.now(timezone.utc)
    review.action_taken = data.action

    result = {"message": "Review resolved", "action": data.action}

    if data.action == "create_new" and data.company_name and data.job_title:
        # Create new application
        app = Application(
            user_id=current_user.id,
            company_name=data.company_name,
            job_title=data.job_title,
            location=data.location,
            application_date=review.raw_email.original_sent_date or review.raw_email.received_datetime,
            first_seen_date=datetime.now(timezone.utc),
            current_status=data.current_status or review.suggested_status or ApplicationStatus.APPLIED_RECEIVED,
            status_updated_at=datetime.now(timezone.utc),
            overall_confidence=review.confidence or 0.5,
            company_confidence=review.confidence or 0.5,
            job_title_confidence=review.confidence or 0.5
        )
        db.add(app)
        db.flush()

        review.created_application_id = app.id
        result["application_id"] = app.id
        result["application_created"] = True

    elif data.action == "link_to_existing" and data.application_id:
        review.application_id = data.application_id
        result["application_id"] = data.application_id
        result["linked"] = True

    db.commit()

    return result


# Stats endpoint

@app.get("/stats")
def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics (user-scoped)"""

    total_apps = db.query(Application).filter(Application.user_id == current_user.id).count()
    pending_actions = db.query(Application).filter(
        Application.user_id == current_user.id,
        Application.action_required == True
    ).count()
    pending_review = db.query(ManualReview).filter(
        ManualReview.user_id == current_user.id,
        ManualReview.reviewed == False
    ).count()

    # By status
    by_status = db.query(
        Application.current_status,
        func.count(Application.id)
    ).filter(Application.user_id == current_user.id).group_by(Application.current_status).all()

    status_counts = {status.value if hasattr(status, 'value') else str(status): count for status, count in by_status}

    # Recent applications
    recent_apps = db.query(Application).filter(
        Application.user_id == current_user.id
    ).order_by(
        desc(Application.first_seen_date)
    ).limit(10).all()

    # Last sync
    last_sync = db.query(SyncState).filter(
        SyncState.user_id == current_user.id
    ).order_by(desc(SyncState.started_at)).first()

    return {
        "total_applications": total_apps,
        "pending_actions": pending_actions,
        "pending_manual_review": pending_review,
        "by_status": status_counts,
        "recent_applications": [
            {
                "id": app.id,
                "company_name": app.company_name,
                "job_title": app.job_title,
                "current_status": app.current_status,
                "first_seen_date": app.first_seen_date,
                "overall_confidence": app.overall_confidence
            }
            for app in recent_apps
        ],
        "last_sync": {
            "completed_at": last_sync.completed_at,
            "emails_fetched": last_sync.emails_fetched,
            "emails_processed": last_sync.emails_processed,
            "applications_created": last_sync.applications_created,
            "success": last_sync.success
        } if last_sync else None
    }


# CSV Export endpoint
from fastapi.responses import StreamingResponse
import csv
import io

@app.get("/applications/export/csv")
def export_applications_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export all applications to CSV"""
    applications = db.query(Application).filter(
        Application.user_id == current_user.id,
        Application.is_archived == False
    ).order_by(desc(Application.first_seen_date)).all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        "Company", "Job Title", "Location", "Status", "Application Date",
        "First Seen", "Action Required", "Action Type", "Action Deadline",
        "Confidence", "Notes"
    ])

    # Data rows
    for app in applications:
        writer.writerow([
            app.company_name,
            app.job_title,
            app.location or "",
            app.current_status.value if app.current_status else "",
            app.application_date.strftime("%Y-%m-%d") if app.application_date else "",
            app.first_seen_date.strftime("%Y-%m-%d") if app.first_seen_date else "",
            "Yes" if app.action_required else "No",
            app.action_type.value if app.action_type else "",
            app.action_deadline.strftime("%Y-%m-%d") if app.action_deadline else "",
            f"{(app.overall_confidence or 0) * 100:.0f}%",
            app.notes or ""
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=job_applications.csv"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
