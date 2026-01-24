"""
Email Processing Pipeline

Orchestrates the full pipeline:
1. Fetch raw emails from Outlook (Microsoft Graph)
2. Unwrap forwarded emails
3. Extract structured data
4. Match to existing applications
5. Upsert to database
6. Handle errors and manual review queue

This is the main processing engine that ties everything together.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass
import logging

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import (
    RawEmail, Application, ApplicationEvent, Link, ManualReview,
    ApplicationStatus, EmailType, LinkType
)
from app.unwrapper import ForwardedEmailUnwrapper, UnwrappedEmail
from app.extractor import JobEmailExtractor, ExtractedData, generate_email_fingerprint
from app.matcher import ApplicationMatcher, MatchResult


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of processing a single email"""
    raw_email_id: int
    success: bool
    application_id: Optional[int]
    is_new_application: bool
    needs_manual_review: bool
    error: Optional[str]
    confidence: float


class EmailProcessor:
    """
    Main email processing pipeline.

    Handles:
    - Unwrapping forwarded emails
    - Extracting structured data
    - Matching to applications
    - Database operations
    - Error handling
    - Manual review routing
    """

    def __init__(self, db: Session, llm_client=None, user_id: int = None):
        """
        Initialize processor.

        Args:
            db: SQLAlchemy session
            llm_client: Optional LLM client for extraction fallback
            user_id: User ID for multi-user support
        """
        self.db = db
        self.user_id = user_id
        self.unwrapper = ForwardedEmailUnwrapper()
        self.extractor = JobEmailExtractor(llm_client=llm_client)
        self.matcher = ApplicationMatcher(db, user_id=user_id)

    def process_email(
        self,
        outlook_message_id: str,
        outlook_from: str,
        outlook_to: str,
        outlook_subject: str,
        received_datetime: datetime,
        body_text: Optional[str],
        body_html: Optional[str],
        raw_headers: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None
    ) -> ProcessingResult:
        """
        Process a single email through the full pipeline.

        Args:
            outlook_message_id: Unique message ID from Outlook
            outlook_from: From address (may be Gmail forwarding)
            outlook_to: To address
            outlook_subject: Subject line
            received_datetime: When Outlook received it
            body_text: Plain text body
            body_html: HTML body
            raw_headers: Optional email headers dict
            conversation_id: Optional Outlook conversation ID

        Returns:
            ProcessingResult with outcome
        """
        try:
            # Step 1: Check if already processed (deduplication) - per user
            existing = self.db.query(RawEmail).filter(
                RawEmail.outlook_message_id == outlook_message_id,
                RawEmail.user_id == self.user_id
            ).first()

            if existing:
                logger.info(f"Email {outlook_message_id} already processed")
                return ProcessingResult(
                    raw_email_id=existing.id,
                    success=True,
                    application_id=existing.events[0].application_id if existing.events else None,
                    is_new_application=False,
                    needs_manual_review=False,
                    error=None,
                    confidence=existing.overall_confidence or 0.0
                )

            # Step 2: Create RawEmail record
            raw_email = RawEmail(
                user_id=self.user_id,
                outlook_message_id=outlook_message_id,
                outlook_conversation_id=conversation_id,
                received_datetime=received_datetime,
                outlook_from=outlook_from,
                outlook_to=outlook_to,
                outlook_subject=outlook_subject,
                body_text=body_text,
                body_html=body_html,
                raw_headers=raw_headers or {},
                processed=False
            )

            self.db.add(raw_email)
            self.db.flush()  # Get ID without committing

            # Step 3: Unwrap forwarded email
            unwrapped = self.unwrapper.unwrap(body_text, body_html)

            raw_email.original_from = unwrapped.original_from
            raw_email.original_subject = unwrapped.original_subject
            raw_email.original_sent_date = unwrapped.original_date
            raw_email.clean_body_text = unwrapped.clean_body_text
            raw_email.clean_body_html = unwrapped.clean_body_html
            raw_email.unwrap_confidence = unwrapped.confidence

            # Step 4: Extract structured data
            extraction_subject = unwrapped.original_subject or outlook_subject
            extraction_body = unwrapped.clean_body_text or body_text or ""
            extraction_from = unwrapped.original_from or outlook_from
            extraction_date = unwrapped.original_date or received_datetime

            extracted_data = self.extractor.extract(
                subject=extraction_subject,
                body=extraction_body,
                from_address=extraction_from,
                date=extraction_date
            )

            # Generate email fingerprint for deduplication
            fingerprint = generate_email_fingerprint(
                original_from=unwrapped.original_from or outlook_from,
                original_subject=unwrapped.original_subject or outlook_subject,
                original_date=unwrapped.original_date,
                body_prefix=(unwrapped.clean_body_text or body_text or "")[:500]
            )

            raw_email.email_fingerprint = fingerprint
            raw_email.email_type = extracted_data.email_type
            raw_email.extracted_data = extracted_data.to_dict()
            raw_email.overall_confidence = extracted_data.overall_confidence
            raw_email.parser_version = extracted_data.parser_version

            # Check fingerprint deduplication - per user
            existing_fingerprint = self.db.query(RawEmail).filter(
                RawEmail.email_fingerprint == fingerprint,
                RawEmail.id != raw_email.id,
                RawEmail.user_id == self.user_id
            ).first()

            if existing_fingerprint:
                logger.info(f"Duplicate email detected via fingerprint: {fingerprint}")
                raw_email.processed = True
                raw_email.processing_error = "Duplicate (fingerprint match)"
                self.db.commit()

                return ProcessingResult(
                    raw_email_id=raw_email.id,
                    success=True,
                    application_id=existing_fingerprint.events[0].application_id if existing_fingerprint.events else None,
                    is_new_application=False,
                    needs_manual_review=False,
                    error="Duplicate email",
                    confidence=extracted_data.overall_confidence
                )

            # Step 5: Match to existing application
            match_result = self.matcher.match(extracted_data, extraction_date)

            # Step 6: Handle matching result
            if match_result.should_review:
                # Route to manual review queue
                self._create_manual_review(raw_email, extracted_data, match_result)
                raw_email.processed = True
                self.db.commit()

                return ProcessingResult(
                    raw_email_id=raw_email.id,
                    success=True,
                    application_id=match_result.application_id,
                    is_new_application=False,
                    needs_manual_review=True,
                    error=None,
                    confidence=match_result.confidence
                )

            elif match_result.is_new:
                # Create new application
                application = self._create_application(extracted_data, extraction_date)
                self._create_event(application, raw_email, extracted_data, extraction_date)
                self._create_links(application, raw_email, extracted_data)

                raw_email.processed = True
                raw_email.processed_at = datetime.utcnow()
                self.db.commit()

                logger.info(f"Created new application: {application.company_name} - {application.job_title}")

                return ProcessingResult(
                    raw_email_id=raw_email.id,
                    success=True,
                    application_id=application.id,
                    is_new_application=True,
                    needs_manual_review=False,
                    error=None,
                    confidence=extracted_data.overall_confidence
                )

            else:
                # Update existing application
                application = self.db.query(Application).get(match_result.application_id)
                if application:
                    self._update_application(application, extracted_data, extraction_date)
                    self._create_event(application, raw_email, extracted_data, extraction_date)
                    self._create_links(application, raw_email, extracted_data)

                    raw_email.processed = True
                    raw_email.processed_at = datetime.utcnow()
                    self.db.commit()

                    logger.info(f"Updated application: {application.company_name} - {application.job_title}")

                    return ProcessingResult(
                        raw_email_id=raw_email.id,
                        success=True,
                        application_id=application.id,
                        is_new_application=False,
                        needs_manual_review=False,
                        error=None,
                        confidence=extracted_data.overall_confidence
                    )

                else:
                    raise Exception(f"Application {match_result.application_id} not found")

        except Exception as e:
            logger.error(f"Error processing email {outlook_message_id}: {str(e)}")
            self.db.rollback()

            # Save error to database if raw_email was created
            if 'raw_email' in locals():
                raw_email.processing_error = str(e)
                raw_email.processed = False
                try:
                    self.db.commit()
                except:
                    pass

            return ProcessingResult(
                raw_email_id=raw_email.id if 'raw_email' in locals() else 0,
                success=False,
                application_id=None,
                is_new_application=False,
                needs_manual_review=False,
                error=str(e),
                confidence=0.0
            )

    def _create_application(
        self,
        extracted_data: ExtractedData,
        email_date: datetime
    ) -> Application:
        """Create new Application record"""
        application = Application(
            user_id=self.user_id,
            company_name=extracted_data.company_name or "Unknown Company",
            job_title=extracted_data.job_title or "Unknown Position",
            location=extracted_data.location,
            application_date=email_date,
            first_seen_date=email_date,
            current_status=extracted_data.status,
            status_updated_at=email_date,
            action_required=extracted_data.action_required,
            action_type=extracted_data.action_type,
            action_deadline=extracted_data.action_deadline,
            action_description=extracted_data.action_description,
            company_confidence=extracted_data.company_confidence,
            job_title_confidence=extracted_data.job_title_confidence,
            overall_confidence=extracted_data.overall_confidence,
            latest_email_date=email_date,
            event_count=0,
            link_count=len(extracted_data.links)
        )

        self.db.add(application)
        self.db.flush()
        return application

    def _update_application(
        self,
        application: Application,
        extracted_data: ExtractedData,
        email_date: datetime
    ):
        """Update existing Application with new data"""
        # Update status if changed
        if extracted_data.status != application.current_status:
            application.current_status = extracted_data.status
            application.status_updated_at = email_date

        # Update action if present
        if extracted_data.action_required:
            application.action_required = True
            application.action_type = extracted_data.action_type
            application.action_deadline = extracted_data.action_deadline
            application.action_description = extracted_data.action_description

        # Update metadata
        if email_date > application.latest_email_date:
            application.latest_email_date = email_date

        application.event_count += 1
        application.link_count += len(extracted_data.links)
        application.updated_at = datetime.utcnow()

    def _create_event(
        self,
        application: Application,
        raw_email: RawEmail,
        extracted_data: ExtractedData,
        event_date: datetime
    ):
        """Create ApplicationEvent record"""
        # Create title from email type and company
        title_map = {
            EmailType.APPLICATION_CONFIRMATION: "Application Received",
            EmailType.REJECTION: "Application Rejected",
            EmailType.ASSESSMENT_INVITE: "Assessment Invited",
            EmailType.INTERVIEW_REQUEST: "Interview Requested",
            EmailType.INTERVIEW_CONFIRMATION: "Interview Scheduled",
            EmailType.OFFER: "Offer Extended",
        }

        title = title_map.get(extracted_data.email_type, "Update")

        event = ApplicationEvent(
            application_id=application.id,
            raw_email_id=raw_email.id,
            event_type=extracted_data.email_type,
            status=extracted_data.status,
            event_date=event_date,
            title=title,
            description=raw_email.clean_body_text[:500] if raw_email.clean_body_text else None,
            extracted_data=extracted_data.to_dict(),
            confidence=extracted_data.overall_confidence
        )

        self.db.add(event)

    def _create_links(
        self,
        application: Application,
        raw_email: RawEmail,
        extracted_data: ExtractedData
    ):
        """Create Link records for extracted URLs"""
        for extracted_link in extracted_data.links:
            link = Link(
                application_id=application.id,
                raw_email_id=raw_email.id,
                url=extracted_link.url,
                link_type=extracted_link.link_type,
                link_text=extracted_link.link_text,
                confidence=extracted_link.confidence,
                expires_at=extracted_data.action_deadline if extracted_data.action_required else None
            )
            self.db.add(link)

    def _create_manual_review(
        self,
        raw_email: RawEmail,
        extracted_data: ExtractedData,
        match_result: MatchResult
    ):
        """Create ManualReview record for low-confidence items"""
        review = ManualReview(
            user_id=self.user_id,
            raw_email_id=raw_email.id,
            application_id=match_result.application_id,
            reason=match_result.reason,
            suggested_company=extracted_data.company_name,
            suggested_job_title=extracted_data.job_title,
            suggested_status=extracted_data.status,
            confidence=match_result.confidence,
            reviewed=False
        )

        self.db.add(review)
        logger.info(f"Created manual review: {match_result.reason}")

    def process_batch(
        self,
        emails: List[Dict[str, Any]]
    ) -> List[ProcessingResult]:
        """
        Process multiple emails in batch.

        Args:
            emails: List of email dicts with keys matching process_email args

        Returns:
            List of ProcessingResult
        """
        results = []

        for email_data in emails:
            result = self.process_email(**email_data)
            results.append(result)

        return results

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        total_emails = self.db.query(RawEmail).count()
        processed = self.db.query(RawEmail).filter(RawEmail.processed == True).count()
        pending_review = self.db.query(ManualReview).filter(ManualReview.reviewed == False).count()
        total_applications = self.db.query(Application).count()

        avg_confidence = self.db.query(func.avg(RawEmail.overall_confidence)).filter(
            RawEmail.processed == True
        ).scalar()

        return {
            "total_emails": total_emails,
            "processed_emails": processed,
            "pending_emails": total_emails - processed,
            "pending_manual_review": pending_review,
            "total_applications": total_applications,
            "average_confidence": float(avg_confidence) if avg_confidence else 0.0
        }


# Convenience functions
def process_outlook_email(
    db: Session,
    message_data: Dict[str, Any],
    llm_client=None
) -> ProcessingResult:
    """
    Convenience wrapper for processing a single Outlook message.

    Usage:
        result = process_outlook_email(db, message_data)

        if result.success:
            if result.is_new_application:
                print(f"Created new application: {result.application_id}")
            elif result.needs_manual_review:
                print("Sent to manual review queue")
            else:
                print(f"Updated application: {result.application_id}")
    """
    processor = EmailProcessor(db, llm_client=llm_client)
    return processor.process_email(**message_data)
