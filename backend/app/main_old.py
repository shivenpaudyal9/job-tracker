"""
FastAPI REST API for Job Tracker

Endpoints:
- GET /applications - List applications with filters
- GET /applications/{id} - Get single application with events
- POST /applications - Create application manually
- PATCH /applications/{id} - Update application
- DELETE /applications/{id} - Delete application

- GET /manual-review - List items needing review
- POST /manual-review/{id}/resolve - Resolve manual review

- POST /sync - Trigger Outlook sync
- POST /export - Generate Excel export

- GET /stats - Dashboard statistics
"""

from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from app.database import get_db, engine
from app.models import (
    Base, Application, ApplicationEvent, ManualReview,
    ApplicationStatus, ActionType
)
from app.graph_client import sync_outlook_emails
from app.excel_exporter import export_to_excel

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI
app = FastAPI(
    title="Job Tracker API",
    description="Production job application tracking system",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
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
    current_status: Optional[ApplicationStatus] = None
    action_required: Optional[bool] = None
    action_type: Optional[ActionType] = None
    action_deadline: Optional[datetime] = None

class ManualReviewResolve(BaseModel):
    action: str  # "create_new", "link_to_existing", "ignore"
    application_id: Optional[int] = None
    company_name: Optional[str] = None
    job_title: Optional[str] = None


# Endpoints

@app.get("/")
def root():
    """API health check"""
    return {"status": "ok", "service": "Job Tracker API", "version": "1.0.0"}


@app.get("/applications")
def list_applications(
    status: Optional[ApplicationStatus] = None,
    company: Optional[str] = None,
    action_required: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List applications with filters"""
    query = db.query(Application)

    if status:
        query = query.filter(Application.current_status == status)
    if company:
        query = query.filter(Application.company_name.ilike(f"%{company}%"))
    if action_required is not None:
        query = query.filter(Application.action_required == action_required)

    total = query.count()
    applications = query.order_by(Application.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": applications
    }


@app.get("/applications/{application_id}")
def get_application(application_id: int, db: Session = Depends(get_db)):
    """Get single application with events and links"""
    app = db.query(Application).filter(Application.id == application_id).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Include events and links
    return {
        "application": app,
        "events": app.events,
        "links": app.links
    }


@app.post("/applications", status_code=201)
def create_application(
    data: ApplicationCreate,
    db: Session = Depends(get_db)
):
    """Create new application manually"""
    app = Application(
        company_name=data.company_name,
        job_title=data.job_title,
        location=data.location,
        application_date=data.application_date or datetime.utcnow(),
        first_seen_date=datetime.utcnow(),
        current_status=data.current_status,
        status_updated_at=datetime.utcnow(),
        overall_confidence=1.0  # Manual entry = high confidence
    )

    db.add(app)
    db.commit()
    db.refresh(app)

    return app


@app.patch("/applications/{application_id}")
def update_application(
    application_id: int,
    data: ApplicationUpdate,
    db: Session = Depends(get_db)
):
    """Update application"""
    app = db.query(Application).filter(Application.id == application_id).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if data.current_status:
        app.current_status = data.current_status
        app.status_updated_at = datetime.utcnow()

    if data.action_required is not None:
        app.action_required = data.action_required

    if data.action_type:
        app.action_type = data.action_type

    if data.action_deadline:
        app.action_deadline = data.action_deadline

    app.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(app)

    return app


@app.delete("/applications/{application_id}")
def delete_application(application_id: int, db: Session = Depends(get_db)):
    """Delete application"""
    app = db.query(Application).filter(Application.id == application_id).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    db.delete(app)
    db.commit()

    return {"message": "Application deleted"}


@app.get("/manual-review")
def list_manual_review(
    reviewed: bool = False,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List items in manual review queue"""
    query = db.query(ManualReview).filter(ManualReview.reviewed == reviewed)

    total = query.count()
    items = query.order_by(ManualReview.created_at.desc()).offset(skip).limit(limit).all()

    # Include raw email data
    result = []
    for item in items:
        result.append({
            "review": item,
            "email": item.raw_email,
            "suggested_matches": []  # Could add matcher.find_candidates() here
        })

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": result
    }


@app.post("/manual-review/{review_id}/resolve")
def resolve_manual_review(
    review_id: int,
    data: ManualReviewResolve,
    db: Session = Depends(get_db)
):
    """Resolve a manual review item"""
    review = db.query(ManualReview).filter(ManualReview.id == review_id).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.reviewed = True
    review.reviewed_at = datetime.utcnow()
    review.action_taken = data.action

    if data.action == "create_new" and data.company_name and data.job_title:
        # Create new application
        app = Application(
            company_name=data.company_name,
            job_title=data.job_title,
            application_date=review.raw_email.original_sent_date or review.raw_email.received_datetime,
            first_seen_date=datetime.utcnow(),
            current_status=review.suggested_status or ApplicationStatus.APPLIED_RECEIVED,
            status_updated_at=datetime.utcnow(),
            overall_confidence=review.confidence or 0.5
        )
        db.add(app)
        db.flush()

        review.created_application_id = app.id

    elif data.action == "link_to_existing" and data.application_id:
        review.application_id = data.application_id

    db.commit()

    return {"message": "Review resolved", "application_id": review.created_application_id or review.application_id}


@app.post("/sync")
def trigger_sync(
    background_tasks: BackgroundTasks,
    days_back: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """Trigger Outlook email sync"""
    def run_sync():
        try:
            result = sync_outlook_emails(db, days_back=days_back)
            logger.info(f"Sync completed: {result}")
        except Exception as e:
            logger.error(f"Sync failed: {e}")

    background_tasks.add_task(run_sync)

    return {"message": "Sync started in background", "days_back": days_back}


@app.post("/export")
def trigger_export(
    background_tasks: BackgroundTasks,
    output_path: str = Query("job_applications.xlsx"),
    db: Session = Depends(get_db)
):
    """Generate Excel export"""
    def run_export():
        try:
            file_path = export_to_excel(db, output_path)
            logger.info(f"Export completed: {file_path}")
        except Exception as e:
            logger.error(f"Export failed: {e}")

    background_tasks.add_task(run_export)

    return {"message": "Export started", "output_path": output_path}


@app.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics"""
    from sqlalchemy import func

    total_apps = db.query(Application).count()
    pending_actions = db.query(Application).filter(Application.action_required == True).count()
    pending_review = db.query(ManualReview).filter(ManualReview.reviewed == False).count()

    # By status
    by_status = db.query(
        Application.current_status,
        func.count(Application.id)
    ).group_by(Application.current_status).all()

    status_counts = {status.value: count for status, count in by_status}

    # Recent applications
    recent_apps = db.query(Application).order_by(
        Application.created_at.desc()
    ).limit(10).all()

    return {
        "total_applications": total_apps,
        "pending_actions": pending_actions,
        "pending_manual_review": pending_review,
        "by_status": status_counts,
        "recent_applications": recent_apps
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
