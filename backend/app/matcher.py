"""
Application Matcher

Matches incoming emails to existing applications in the database.

Challenge: Forwarding breaks email threading, so we can't rely on conversation_id.
Solution: Multi-strategy matching with confidence scoring.

Strategies:
1. Strong match: company_name + job_title exact/fuzzy match
2. Medium match: domain + recent applications
3. Weak match: subject similarity + time window
4. No match: create new application or route to manual review
"""

from typing import Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models import Application, ApplicationStatus
from app.extractor import ExtractedData


@dataclass
class MatchResult:
    """Result of application matching"""
    application_id: Optional[int]
    match_type: str  # "exact", "fuzzy", "domain", "subject", "no_match"
    confidence: float  # 0.0-1.0
    is_new: bool  # True if should create new application
    should_review: bool  # True if needs manual review
    reason: str  # Explanation of match/no-match


class ApplicationMatcher:
    """
    Matches emails to existing applications using multiple strategies.

    Priority order:
    1. Exact company + job_title match
    2. Fuzzy company + job_title match (>80% similarity)
    3. Domain match + time window + subject similarity
    4. Create new or manual review
    """

    # Thresholds
    FUZZY_MATCH_THRESHOLD = 0.80  # 80% similarity for fuzzy matching
    TIME_WINDOW_DAYS = 60  # Look for applications within 60 days
    LOW_CONFIDENCE_THRESHOLD = 0.6  # Below this, route to manual review

    def __init__(self, db: Session, user_id: int = None):
        """
        Initialize matcher.

        Args:
            db: SQLAlchemy database session
            user_id: User ID for multi-user support
        """
        self.db = db
        self.user_id = user_id

    def match(
        self,
        extracted_data: ExtractedData,
        email_date: datetime
    ) -> MatchResult:
        """
        Main matching entry point.

        Args:
            extracted_data: Data extracted from email
            email_date: When email was sent

        Returns:
            MatchResult with application_id and confidence
        """
        company = extracted_data.company_name
        job_title = extracted_data.job_title

        # Strategy 1: Exact match
        if company and job_title:
            result = self._match_exact(company, job_title)
            if result:
                return result

        # Strategy 2: Fuzzy match
        if company and job_title:
            result = self._match_fuzzy(company, job_title)
            if result:
                return result

        # Strategy 3: Domain + time window
        if company:
            result = self._match_by_domain_and_time(company, email_date)
            if result:
                return result

        # Strategy 4: Subject similarity (weakest)
        if extracted_data.job_title:
            result = self._match_by_subject_similarity(
                extracted_data.job_title,
                email_date
            )
            if result:
                return result

        # No match found - decide: create new or manual review
        return self._handle_no_match(extracted_data)

    def _match_exact(self, company: str, job_title: str) -> Optional[MatchResult]:
        """
        Exact match on company_name and job_title.

        Case-insensitive, strips whitespace.
        """
        company_clean = company.strip().lower()
        job_title_clean = job_title.strip().lower()

        query = self.db.query(Application).filter(
            and_(
                func.lower(Application.company_name) == company_clean,
                func.lower(Application.job_title) == job_title_clean
            )
        )
        if self.user_id:
            query = query.filter(Application.user_id == self.user_id)
        application = query.first()

        if application:
            return MatchResult(
                application_id=application.id,
                match_type="exact",
                confidence=1.0,
                is_new=False,
                should_review=False,
                reason=f"Exact match: {company} - {job_title}"
            )

        return None

    def _match_fuzzy(self, company: str, job_title: str) -> Optional[MatchResult]:
        """
        Fuzzy match using string similarity.

        Finds applications with similar company + job_title.
        """
        # Get all applications from DB (in production, add pagination)
        query = self.db.query(Application).filter(
            Application.created_at >= datetime.utcnow() - timedelta(days=self.TIME_WINDOW_DAYS)
        )
        if self.user_id:
            query = query.filter(Application.user_id == self.user_id)
        recent_applications = query.all()

        best_match = None
        best_similarity = 0.0

        for app in recent_applications:
            # Calculate similarity for both company and job_title
            company_sim = self._string_similarity(
                company.lower(),
                app.company_name.lower()
            )
            job_title_sim = self._string_similarity(
                job_title.lower(),
                app.job_title.lower()
            )

            # Combined similarity (weighted average)
            combined_sim = (company_sim * 0.6) + (job_title_sim * 0.4)

            if combined_sim > best_similarity and combined_sim >= self.FUZZY_MATCH_THRESHOLD:
                best_similarity = combined_sim
                best_match = app

        if best_match:
            return MatchResult(
                application_id=best_match.id,
                match_type="fuzzy",
                confidence=best_similarity,
                is_new=False,
                should_review=best_similarity < 0.90,  # Manual review if < 90%
                reason=f"Fuzzy match ({best_similarity:.2f}): {best_match.company_name} - {best_match.job_title}"
            )

        return None

    def _match_by_domain_and_time(
        self,
        company: str,
        email_date: datetime
    ) -> Optional[MatchResult]:
        """
        Match by company name within time window.

        Useful when job_title extraction failed but we have company.
        """
        company_clean = company.strip().lower()

        # Find applications from same company in recent time window
        query = self.db.query(Application).filter(
            and_(
                func.lower(Application.company_name).like(f"%{company_clean}%"),
                Application.latest_email_date >= email_date - timedelta(days=self.TIME_WINDOW_DAYS)
            )
        )
        if self.user_id:
            query = query.filter(Application.user_id == self.user_id)
        applications = query.order_by(Application.latest_email_date.desc()).all()

        if len(applications) == 1:
            # Only one matching application - likely correct
            app = applications[0]
            return MatchResult(
                application_id=app.id,
                match_type="domain_time",
                confidence=0.75,
                is_new=False,
                should_review=True,  # Always review domain+time matches
                reason=f"Single application found for {company} in time window"
            )

        elif len(applications) > 1:
            # Multiple matches - need manual review
            return MatchResult(
                application_id=None,
                match_type="domain_time_ambiguous",
                confidence=0.5,
                is_new=False,
                should_review=True,
                reason=f"Multiple applications found for {company} - manual review needed"
            )

        return None

    def _match_by_subject_similarity(
        self,
        job_title: str,
        email_date: datetime
    ) -> Optional[MatchResult]:
        """
        Weakest match: find applications with similar job titles.

        Used as last resort when company extraction failed.
        """
        query = self.db.query(Application).filter(
            Application.latest_email_date >= email_date - timedelta(days=30)
        )
        if self.user_id:
            query = query.filter(Application.user_id == self.user_id)
        recent_applications = query.all()

        best_match = None
        best_similarity = 0.0

        for app in recent_applications:
            similarity = self._string_similarity(
                job_title.lower(),
                app.job_title.lower()
            )

            if similarity > best_similarity and similarity >= 0.85:  # High threshold
                best_similarity = similarity
                best_match = app

        if best_match:
            return MatchResult(
                application_id=best_match.id,
                match_type="subject_similarity",
                confidence=best_similarity * 0.7,  # Reduce confidence due to weak match
                is_new=False,
                should_review=True,  # Always review subject-only matches
                reason=f"Job title similarity ({best_similarity:.2f}): {best_match.job_title}"
            )

        return None

    def _handle_no_match(self, extracted_data: ExtractedData) -> MatchResult:
        """
        Decide what to do when no match is found.

        - High confidence extraction → create new application
        - Low confidence → route to manual review
        """
        if extracted_data.overall_confidence >= self.LOW_CONFIDENCE_THRESHOLD:
            # Good extraction, safe to create new application
            return MatchResult(
                application_id=None,
                match_type="no_match",
                confidence=extracted_data.overall_confidence,
                is_new=True,
                should_review=False,
                reason="No existing match found - creating new application"
            )
        else:
            # Low confidence - needs human review
            return MatchResult(
                application_id=None,
                match_type="no_match_low_confidence",
                confidence=extracted_data.overall_confidence,
                is_new=False,
                should_review=True,
                reason=f"Low extraction confidence ({extracted_data.overall_confidence:.2f}) - manual review required"
            )

    def _string_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate string similarity using SequenceMatcher.

        Returns value between 0.0 (no match) and 1.0 (exact match).
        """
        return SequenceMatcher(None, str1, str2).ratio()

    def find_candidates(
        self,
        company: Optional[str],
        job_title: Optional[str],
        limit: int = 5
    ) -> List[Tuple[Application, float]]:
        """
        Find candidate applications for manual review UI.

        Returns list of (Application, similarity_score) tuples.
        """
        if not company and not job_title:
            return []

        candidates = []
        query = self.db.query(Application).filter(
            Application.created_at >= datetime.utcnow() - timedelta(days=self.TIME_WINDOW_DAYS)
        )
        if self.user_id:
            query = query.filter(Application.user_id == self.user_id)
        recent_applications = query.all()

        for app in recent_applications:
            score = 0.0

            if company:
                company_sim = self._string_similarity(
                    company.lower(),
                    app.company_name.lower()
                )
                score += company_sim * 0.6

            if job_title:
                job_title_sim = self._string_similarity(
                    job_title.lower(),
                    app.job_title.lower()
                )
                score += job_title_sim * 0.4

            if score > 0.5:  # Only include reasonable matches
                candidates.append((app, score))

        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)

        return candidates[:limit]


# Convenience function
def match_email_to_application(
    db: Session,
    extracted_data: ExtractedData,
    email_date: datetime
) -> MatchResult:
    """
    Convenience function to match an email to an application.

    Usage:
        result = match_email_to_application(db, extracted_data, email_date)

        if result.is_new:
            # Create new application
        elif result.should_review:
            # Add to manual review queue
        else:
            # Update existing application
    """
    matcher = ApplicationMatcher(db)
    return matcher.match(extracted_data, email_date)
