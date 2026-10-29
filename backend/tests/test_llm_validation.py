"""Regression and SQLite integration tests for selective email automation."""
import json
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.extractor import JobEmailExtractor
from app.llm_validation import validate_llm_payload
from app.llm_decision import verify_llm_status, status_signals
from app.matcher import ApplicationMatcher
from app.models import (
    Base, User, Application, ApplicationStatus,
    RawEmail, ApplicationEvent, ManualReview,
)
from app.processor import EmailProcessor


SUBJECT = "Amazon Software Engineer application"
BODY = (
    "Thank you for applying to Amazon for the Software Engineer position. "
    "Please complete your coding assessment."
)
SENDER = "recruiting@amazon.com"
TODAY = datetime(2026, 10, 29, 14, 0)


def good_payload():
    return {
        "company_name": "Amazon",
        "company_evidence": "applying to Amazon",
        "job_title": "Software Engineer",
        "job_title_evidence": "Software Engineer position",
        "status": "assessment",
        "status_evidence": "Please complete your coding assessment",
        "action_required": True,
        "action_description": "Complete coding assessment",
        "action_evidence": "complete your coding assessment",
        "is_job_related": True,
    }


class FakeGroq:
    def __init__(self, payload):
        self.payload = payload
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **_kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(self.payload)))]
        )


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    session.add(User(id=1, email="candidate@example.com", hashed_password="unused"))
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def app_row(db, status=ApplicationStatus.APPLIED_RECEIVED, job_title="Software Engineer",
            when=None):
    app = Application(
        user_id=1, company_name="Amazon", job_title=job_title,
        first_seen_date=TODAY - timedelta(days=5),
        current_status=status,
        status_updated_at=when or (TODAY - timedelta(days=2)),
        latest_email_date=TODAY - timedelta(days=2),
        event_count=0, link_count=0,
    )
    db.add(app)
    db.commit()
    return app


def process(db, payload, message_id="email-1", body=BODY, subject=SUBJECT, when=TODAY):
    return EmailProcessor(db, llm_client=FakeGroq(payload), user_id=1).process_email(
        outlook_message_id=message_id, outlook_from=SENDER,
        outlook_to="candidate@example.com", outlook_subject=subject,
        received_datetime=when, body_text=body, body_html=None,
    )


def test_rejects_ungrounded_hallucinated_company():
    p = good_payload()
    p["company_name"] = "Microsoft"
    assert validate_llm_payload(p, SUBJECT, BODY, SENDER) is None


def test_rejects_invalid_status_or_irrelevant_email():
    p = good_payload()
    p["status"] = "hired"
    assert validate_llm_payload(p, SUBJECT, BODY, SENDER) is None
    p = good_payload()
    p["is_job_related"] = False
    assert validate_llm_payload(p, SUBJECT, BODY, SENDER) is None


def test_rejects_missing_or_fabricated_evidence():
    p = good_payload()
    p.pop("status_evidence")
    assert validate_llm_payload(p, SUBJECT, BODY, SENDER) is None
    p = good_payload()
    p["status_evidence"] = "You are hired!"
    assert validate_llm_payload(p, SUBJECT, BODY, SENDER) is None


def test_rejects_invented_action_evidence():
    p = good_payload()
    p["action_evidence"] = "send your password"
    assert validate_llm_payload(p, SUBJECT, BODY, SENDER) is None


def test_verifier_allows_application_receipt_plus_clear_assessment():
    score, auto, reason = verify_llm_status(
        "assessment", "Please complete your coding assessment",
        SUBJECT + " " + BODY, "applied",
    )
    assert score == 95
    assert auto is True
    assert "source-backed" in reason


def test_verifier_rejects_ambiguous_non_actionable_evidence():
    score, auto, _ = verify_llm_status(
        "assessment", "Your next phase is exciting",
        "Your next phase is exciting", "other",
    )
    assert score < 95 and not auto


def test_verifier_rejects_conflicting_statuses():
    text = BODY + " We regret to inform you that we are not moving forward."
    score, auto, _ = verify_llm_status(
        "assessment", "Please complete your coding assessment",
        text, "applied",
    )
    assert auto is False
    assert score < 95


def test_verifier_rejects_negated_assessment():
    score, auto, _ = verify_llm_status(
        "assessment", "You do not need to complete an assessment.",
        "You do not need to complete an assessment.", "other",
    )
    assert not auto


def test_llm_auto_eligible_with_verifiable_status_not_fake_probability():
    result = JobEmailExtractor(llm_client=FakeGroq(good_payload())).extract(
        SUBJECT, BODY, SENDER, TODAY
    )
    assert result.extraction_method == "llm_groq_verified"
    assert result.overall_confidence is None
    assert result.verification_score == 95
    assert result.requires_manual_review is False
    assert result.status == ApplicationStatus.NEXT_STEP_ASSESSMENT


def test_llm_unknown_meaning_requires_review():
    body = (
        "Amazon would like to explore your candidacy for the Software Engineer position. "
        "We look forward to discussing your next phase."
    )
    p = good_payload()
    p["company_evidence"] = "Amazon would like to explore your candidacy"
    p["job_title_evidence"] = "Software Engineer position"
    p["status_evidence"] = "We look forward to discussing your next phase"
    p["action_required"] = False
    p["action_description"] = None
    p["action_evidence"] = None
    result = JobEmailExtractor(llm_client=FakeGroq(p)).extract(
        SUBJECT, body, SENDER, TODAY
    )
    assert result.requires_manual_review


def test_invalid_llm_result_falls_back_to_rules():
    p = good_payload()
    p["status_evidence"] = "nonexistent phrase"
    result = JobEmailExtractor(llm_client=FakeGroq(p)).extract(
        SUBJECT, BODY, SENDER, TODAY
    )
    assert result.extraction_method == "rule_based"


def test_exact_application_match_allows_verified_llm_auto(db):
    app = app_row(db)
    result = JobEmailExtractor(llm_client=FakeGroq(good_payload())).extract(
        SUBJECT, BODY, SENDER, TODAY
    )
    match = ApplicationMatcher(db, user_id=1).match(result, TODAY)
    assert match.application_id == app.id
    assert match.should_review is False
    assert match.match_type == "exact"


def test_fuzzy_match_still_needs_review_for_llm(db):
    app_row(db, job_title="Software Engineering")
    result = JobEmailExtractor(llm_client=FakeGroq(good_payload())).extract(
        SUBJECT, BODY, SENDER, TODAY
    )
    match = ApplicationMatcher(db, user_id=1).match(result, TODAY)
    assert match.should_review is True


def test_no_match_assessment_invitation_routes_to_review(db):
    result = JobEmailExtractor(llm_client=FakeGroq(good_payload())).extract(
        SUBJECT, BODY, SENDER, TODAY
    )
    match = ApplicationMatcher(db, user_id=1).match(result, TODAY)
    assert match.should_review and not match.is_new


def test_verified_application_confirmation_can_create_new_application(db):
    subject = "Your application for Software Engineer at Amazon"
    body = "Thank you for applying to Amazon for the Software Engineer position."
    p = good_payload()
    p["status"] = "applied"
    p["status_evidence"] = "Thank you for applying"
    p["action_required"] = False
    p["action_description"] = None
    p["action_evidence"] = None
    result = process(db, p, body=body, subject=subject)
    assert result.success and result.is_new_application
    assert db.query(Application).count() == 1
    assert db.query(ApplicationEvent).count() == 1


def test_existing_application_auto_updates_correctly_and_is_idempotent(db):
    application = app_row(db)
    result = process(db, good_payload())
    db.refresh(application)
    assert result.success and not result.needs_manual_review, result.error
    assert application.current_status == ApplicationStatus.NEXT_STEP_ASSESSMENT
    assert db.query(ApplicationEvent).count() == 1
    repeated = process(db, good_payload())
    assert repeated.success and not repeated.is_new_application
    assert db.query(ApplicationEvent).count() == 1


def test_stale_older_email_requires_review(db):
    application = app_row(
        db, status=ApplicationStatus.INTERVIEW_SCHEDULED,
        when=TODAY + timedelta(hours=2),
    )
    result = process(db, good_payload())
    db.refresh(application)
    assert result.success and result.needs_manual_review, result.error
    assert application.current_status == ApplicationStatus.INTERVIEW_SCHEDULED
    assert db.query(ManualReview).count() == 1
    assert db.query(ApplicationEvent).count() == 0


def test_ambiguous_llm_goes_to_review_without_changing_status(db):
    application = app_row(db)
    p = good_payload()
    p["status_evidence"] = "Thank you for applying to Amazon"
    result = process(db, p)
    db.refresh(application)
    assert result.success and result.needs_manual_review, result.error
    assert application.current_status == ApplicationStatus.APPLIED_RECEIVED
    assert db.query(ManualReview).count() == 1


def test_clear_rejection_with_rule_agreement_may_automate(db):
    application = app_row(db)
    body = (
        "We regret to inform you that Amazon is not moving forward "
        "with your Software Engineer application."
    )
    p = {
        "company_name": "Amazon",
        "company_evidence": "Amazon is not moving forward",
        "job_title": "Software Engineer",
        "job_title_evidence": "Software Engineer application",
        "status": "rejected",
        "status_evidence": "regret to inform you that Amazon is not moving forward",
        "action_required": False,
        "action_description": None,
        "action_evidence": None,
        "is_job_related": True,
    }
    result = process(db, p, body=body, subject="Update on your Amazon application")
    db.refresh(application)
    assert result.success and not result.needs_manual_review, result.error
    assert application.current_status == ApplicationStatus.REJECTED


def test_unproven_offer_phrase_not_auto_accepted():
    score, auto, _ = verify_llm_status(
        "offer", "We have something to offer",
        "We have something to offer", "other",
    )
    assert not auto


def test_interview_scheduling_request_auto_updates_exact_match(db):
    app = app_row(db)
    body = "Please schedule an interview for the Software Engineer role at Amazon."
    payload = {
        "company_name": "Amazon",
        "company_evidence": "role at Amazon",
        "job_title": "Software Engineer",
        "job_title_evidence": "Software Engineer role",
        "status": "interview_request",
        "status_evidence": "Please schedule an interview",
        "action_required": True,
        "action_description": "Schedule interview",
        "action_evidence": "Please schedule an interview",
        "is_job_related": True,
    }
    result = process(db, payload, body=body, subject="Amazon Software Engineer interview invitation")
    db.refresh(app)
    assert result.success and not result.needs_manual_review, result.error
    assert app.current_status == ApplicationStatus.NEXT_STEP_SCHEDULING


def test_stage_regression_requires_review_even_for_newer_email(db):
    app = app_row(db, status=ApplicationStatus.INTERVIEW_SCHEDULED)
    result = process(db, good_payload(), when=TODAY)
    db.refresh(app)
    assert result.success and result.needs_manual_review, result.error
    assert app.current_status == ApplicationStatus.INTERVIEW_SCHEDULED
    assert db.query(ManualReview).count() == 1
