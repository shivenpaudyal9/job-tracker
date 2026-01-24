"""
Email Classification and Data Extraction Engine

Two-layer approach:
1. Deterministic rules (sender domains, subject patterns, keywords)
2. LLM fallback for ambiguous cases (returns structured JSON)

Extracts:
- Company name, job title, location
- Status/stage (normalized)
- Action required + type + deadline
- Links + link types
- Confidence scores per field
"""

import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import hashlib
from app.models import ApplicationStatus, ActionType, EmailType, LinkType


@dataclass
class ExtractedLink:
    """Extracted link with type classification"""
    url: str
    link_type: LinkType
    link_text: Optional[str] = None
    confidence: float = 0.0


@dataclass
class ExtractedData:
    """Complete extraction result from an email"""
    # Core fields
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    location: Optional[str] = None

    # Status
    email_type: EmailType = EmailType.UNKNOWN
    status: ApplicationStatus = ApplicationStatus.OTHER_UPDATE
    status_date: Optional[datetime] = None

    # Action tracking
    action_required: bool = False
    action_type: Optional[ActionType] = None
    action_deadline: Optional[datetime] = None
    action_description: Optional[str] = None

    # Links
    links: List[ExtractedLink] = field(default_factory=list)

    # Confidence scores (0.0-1.0)
    company_confidence: float = 0.0
    job_title_confidence: float = 0.0
    overall_confidence: float = 0.0

    # Metadata
    extraction_method: str = "rule_based"  # "rule_based" or "llm_fallback"
    parser_version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage"""
        data = {
            'company_name': self.company_name,
            'job_title': self.job_title,
            'location': self.location,
            'email_type': self.email_type.value if self.email_type else None,
            'status': self.status.value if self.status else None,
            'status_date': self.status_date.isoformat() if self.status_date else None,
            'action_required': self.action_required,
            'action_type': self.action_type.value if self.action_type else None,
            'action_deadline': self.action_deadline.isoformat() if self.action_deadline else None,
            'action_description': self.action_description,
            'links': [{'url': link.url, 'type': link.link_type.value, 'text': link.link_text}
                     for link in self.links],
            'company_confidence': self.company_confidence,
            'job_title_confidence': self.job_title_confidence,
            'overall_confidence': self.overall_confidence,
            'extraction_method': self.extraction_method,
            'parser_version': self.parser_version,
        }
        return data


class JobEmailExtractor:
    """
    Extracts structured job application data from emails.

    Uses deterministic rules + heuristics with confidence scoring.
    Falls back to LLM only when confidence < threshold.
    """

    # ATS/Recruiter domain patterns
    ATS_DOMAINS = {
        'workday.com': 'Workday',
        'myworkdaysite.com': 'Workday',
        'greenhouse.io': 'Greenhouse',
        'lever.co': 'Lever',
        'icims.com': 'iCIMS',
        'smartrecruiters.com': 'SmartRecruiters',
        'ashbyhq.com': 'Ashby',
        'breezy.hr': 'Breezy HR',
        'jobvite.com': 'Jobvite',
    }

    # Common assessment/scheduling platforms
    ASSESSMENT_DOMAINS = {
        'hackerrank.com': LinkType.ASSESSMENT_PORTAL,
        'codesignal.com': LinkType.ASSESSMENT_PORTAL,
        'codility.com': LinkType.ASSESSMENT_PORTAL,
        'leetcode.com': LinkType.ASSESSMENT_PORTAL,
        'testgorilla.com': LinkType.ASSESSMENT_PORTAL,
    }

    SCHEDULING_DOMAINS = {
        'calendly.com': LinkType.SCHEDULING_LINK,
        'calendar.google.com': LinkType.SCHEDULING_LINK,
        'outlook.office.com': LinkType.SCHEDULING_LINK,
        'when2meet.com': LinkType.SCHEDULING_LINK,
    }

    VIDEO_DOMAINS = {
        'zoom.us': LinkType.VIDEO_INTERVIEW,
        'teams.microsoft.com': LinkType.VIDEO_INTERVIEW,
        'meet.google.com': LinkType.VIDEO_INTERVIEW,
        'webex.com': LinkType.VIDEO_INTERVIEW,
    }

    def __init__(self, llm_client=None):
        """
        Initialize extractor.

        Args:
            llm_client: Optional LLM client for fallback (OpenAI, Anthropic, etc.)
        """
        self.llm_client = llm_client

    def extract(
        self,
        subject: str,
        body: str,
        from_address: str,
        date: Optional[datetime] = None
    ) -> ExtractedData:
        """
        Main extraction entry point.

        Args:
            subject: Email subject line
            body: Email body (plain text)
            from_address: Sender email address
            date: Email sent date

        Returns:
            ExtractedData with all extracted fields and confidence scores
        """
        # Try rule-based extraction first
        result = self._extract_rule_based(subject, body, from_address, date)

        # If confidence too low, try LLM fallback (use LLM more aggressively)
        if result.overall_confidence < 0.85 and self.llm_client:
            llm_result = self._extract_llm_fallback(subject, body, from_address)
            if llm_result and llm_result.overall_confidence > result.overall_confidence:
                result = llm_result

        return result

    def _extract_rule_based(
        self,
        subject: str,
        body: str,
        from_address: str,
        date: Optional[datetime]
    ) -> ExtractedData:
        """Rule-based extraction using patterns and heuristics"""
        result = ExtractedData()
        result.status_date = date or datetime.utcnow()
        result.extraction_method = "rule_based"

        # Combined text for analysis
        text = f"{subject}\n{body}".lower()

        # 1. Classify email type
        result.email_type = self._classify_email_type(subject, body)

        # 2. Extract status based on email type
        result.status = self._extract_status(result.email_type, text)

        # 3. Extract company name
        result.company_name, result.company_confidence = self._extract_company(
            subject, body, from_address
        )

        # 4. Extract job title
        result.job_title, result.job_title_confidence = self._extract_job_title(
            subject, body
        )

        # 5. Extract location
        result.location = self._extract_location(body)

        # 6. Detect actions
        (result.action_required, result.action_type,
         result.action_deadline, result.action_description) = self._detect_action(text, date)

        # 7. Extract links
        result.links = self._extract_links(body)

        # 8. Calculate overall confidence
        result.overall_confidence = self._calculate_overall_confidence(result)

        return result

    def _classify_email_type(self, subject: str, body: str) -> EmailType:
        """Classify the type of email based on patterns"""
        text = f"{subject} {body}".lower()

        # Application confirmation
        if any(pattern in text for pattern in [
            'application received',
            'application was sent',
            'thank you for applying',
            'thank you for your application',
            'we have received your application',
            'application confirmation',
            'successfully submitted',
            'applied on',
        ]):
            return EmailType.APPLICATION_CONFIRMATION

        # Rejection
        if any(pattern in text for pattern in [
            'not moving forward',
            'decided to move forward with other candidates',
            'not selected',
            'unfortunately',
            'regret to inform',
            'pursue other candidates',
            'will not be proceeding',
        ]):
            return EmailType.REJECTION

        # Assessment
        if any(pattern in text for pattern in [
            'coding challenge',
            'technical assessment',
            'complete the assessment',
            'hackerrank',
            'codesignal',
            'take-home',
        ]):
            return EmailType.ASSESSMENT_INVITE

        # Interview request/scheduling
        if any(pattern in text for pattern in [
            'schedule an interview',
            'interview invitation',
            'would like to interview',
            'calendar',
            'availability',
            'please let us know',
            'select a time',
        ]):
            return EmailType.INTERVIEW_REQUEST

        # Interview confirmation
        if any(pattern in text for pattern in [
            'interview is scheduled',
            'confirmed for',
            'interview details',
            'zoom link',
            'meeting link',
        ]):
            return EmailType.INTERVIEW_CONFIRMATION

        # Offer
        if any(pattern in text for pattern in [
            'offer',
            'extend an offer',
            'pleased to offer',
            'compensation',
            'offer letter',
        ]):
            return EmailType.OFFER

        # General update
        if any(pattern in text for pattern in [
            'update',
            'status',
            'wanted to reach out',
        ]):
            return EmailType.GENERAL_UPDATE

        return EmailType.UNKNOWN

    def _extract_status(self, email_type: EmailType, text: str) -> ApplicationStatus:
        """Map email type to application status"""
        mapping = {
            EmailType.APPLICATION_CONFIRMATION: ApplicationStatus.APPLIED_RECEIVED,
            EmailType.REJECTION: ApplicationStatus.REJECTED,
            EmailType.ASSESSMENT_INVITE: ApplicationStatus.NEXT_STEP_ASSESSMENT,
            EmailType.INTERVIEW_REQUEST: ApplicationStatus.NEXT_STEP_SCHEDULING,
            EmailType.INTERVIEW_CONFIRMATION: ApplicationStatus.INTERVIEW_SCHEDULED,
            EmailType.OFFER: ApplicationStatus.OFFER_EXTENDED,
        }

        return mapping.get(email_type, ApplicationStatus.OTHER_UPDATE)

    def _extract_company(
        self,
        subject: str,
        body: str,
        from_address: str
    ) -> tuple[Optional[str], float]:
        """Extract company name with confidence score"""
        company = None
        confidence = 0.0

        # Try multiple strategies, prioritize higher confidence matches

        # Strategy 1: LinkedIn notification format
        if 'linkedin.com' in from_address.lower():
            # "Your application was sent to COMPANY_NAME"
            linkedin_match = re.search(r'application was sent to\s+([A-Z][A-Za-z0-9\s&.]+)', subject, re.IGNORECASE)
            if linkedin_match:
                company = linkedin_match.group(1).strip()
                confidence = 0.9
                return (company, confidence)

        # Strategy 2: Workday subdomain extraction
        # Example: gnw@myworkday.com, hiring@myworkdaysite.com
        if 'myworkday' in from_address.lower():
            workday_match = re.match(r'([a-z]+)@myworkday', from_address.lower())
            if workday_match:
                subdomain = workday_match.group(1)
                # Try to find full company name in body
                body_patterns = [
                    r'interest in employment.*?with\s+([A-Z][A-Za-z0-9\s&.]{2,40}?)\s+and',
                    r'interest in\s+([A-Z][A-Za-z0-9\s&.]{2,40}?)\s+and',
                    r'Sincerely,\s*\n\s*([A-Z][A-Za-z0-9\s&.]+?)\s+(?:Recruitment|Recruiting|Team)',
                    r'Thank you.*?interest in\s+([A-Z][A-Za-z0-9\s&.]{2,40}?)\.',
                ]
                for pattern in body_patterns:
                    match = re.search(pattern, body)
                    if match:
                        company = match.group(1).strip()
                        confidence = 0.9
                        return (company, confidence)

        # Strategy 3: Subject line patterns (high confidence)
        subject_patterns = [
            # "Your application was sent to COMPANY"
            r'application was sent to\s+([A-Z][A-Za-z0-9\s&.]+?)$',
            # "Your application to COMPANY"
            r'application to\s+([A-Z][A-Za-z0-9\s&.]+?)$',
            # "COMPANY - Job Title" or "Job Title - COMPANY"
            r'^([A-Z][A-Za-z0-9\s&.]{2,40}?)\s+-\s+',
            # "Thank you for applying to COMPANY"
            r'thank you for applying to\s+([A-Z][A-Za-z0-9\s&.]+)',
        ]

        for pattern in subject_patterns:
            match = re.search(pattern, subject)
            if match:
                extracted = match.group(1).strip()
                # Filter out common false positives
                false_positives = ['application received', 'thank you', 'your application',
                                   'next phase', 'update from', 'your update from', 'online assessment',
                                   'default directory', 'email', 'your']
                # Also filter if it starts with "Your" (likely a job title pattern)
                if (len(extracted) > 2 and
                    extracted.lower() not in false_positives and
                    not extracted.lower().startswith('your ') and
                    not extracted.lower().startswith('account')):
                    company = extracted
                    confidence = 0.85
                    break

        # Strategy 4: Body patterns (medium-high confidence)
        if not company or confidence < 0.8:
            body_patterns = [
                # "Thank you for submitting an application to COMPANY"
                r'application to\s+([A-Z][A-Za-z0-9\s&.]{2,40}?)[.\n]',
                # "Thank you for your interest in COMPANY"
                r'interest in employment.*?with\s+([A-Z][A-Za-z0-9\s&.]{2,40}?)\s+and',
                r'interest in\s+([A-Z][A-Za-z0-9\s&.]{2,40}?)\s+and',
                r'interest in\s+([A-Z][A-Za-z0-9\s&.]{2,40}?)\!',
                # "Thank you for applying to COMPANY for"
                r'thank you for.*?applying to\s+([A-Z][A-Za-z0-9\s&.]{2,40}?)\s+for',
                # "position at COMPANY"
                r'position at\s+([A-Z][A-Za-z0-9\s&.]{2,40}?)\s+in',
                r'position at\s+([A-Z][A-Za-z0-9\s&.]{2,40}?)[.\n,]',
                # "COMPANY has invited you"
                r'([A-Z][A-Za-z0-9\s&.]{2,40}?)\s+has invited you',
                # "team at COMPANY"
                r'team at\s+([A-Z][A-Za-z0-9\s&.]{2,40}?)[\n.]',
                # Signature: "Sincerely, COMPANY Team"
                r'Sincerely,\s*\n\s*(?:The\s+)?([A-Z][A-Za-z0-9\s&.]+?)\s+(?:Recruitment|Recruiting|Team)',
                # "Thanks again, COMPANY"
                r'Thanks.*?again,\s*\n\s*([A-Z][A-Za-z0-9\s&.]+?)(?:\s|$)',
            ]

            for pattern in body_patterns:
                match = re.search(pattern, body)
                if match:
                    extracted = match.group(1).strip()
                    if len(extracted) > 2 and confidence < 0.85:
                        company = extracted
                        confidence = 0.85
                        break

        # Strategy 5: From domain (if not ATS or personal email) - lowest priority
        if not company or confidence < 0.5:
            domain = from_address.split('@')[-1] if '@' in from_address else ''
            # Skip common personal email providers and ATS domains
            skip_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'live.com',
                           'icloud.com', 'aol.com', 'protonmail.com', 'mail.com', 'zoho.com']
            if domain and not any(ats in domain for ats in self.ATS_DOMAINS.keys()) and domain.lower() not in skip_domains:
                # Clean domain to company name
                company_from_domain = domain.replace('.com', '').replace('.io', '').replace('.co', '')
                company_from_domain = company_from_domain.replace('-', ' ').replace('_', ' ').title()
                if len(company_from_domain) > 2:
                    company = company_from_domain
                    confidence = 0.5

        # Clean up company name
        if company:
            # Remove common trailing words
            company = re.sub(r'\s+(Team|Recruitment|Recruiting|Services|Careers|Online Assessment)$', '', company, flags=re.IGNORECASE)
            company = company.strip()

        return (company, confidence) if company else (None, 0.0)

    def _extract_job_title(self, subject: str, body: str) -> tuple[Optional[str], float]:
        """Extract job title with confidence score"""
        job_title = None
        confidence = 0.0

        # Common job title keywords to help identify titles
        job_keywords = r'(?:Engineer|Developer|Manager|Analyst|Designer|Scientist|Architect|Lead|Senior|Junior|' \
                       r'Intern|Associate|Director|Coordinator|Specialist|Administrator|Consultant|Executive|' \
                       r'Representative|Assistant|Officer|Technician|Support|Sales|Marketing|Product|Software|' \
                       r'Data|Frontend|Backend|Full[\s-]?Stack|DevOps|Cloud|ML|AI|QA|Test|Mobile|Web|UI|UX|HR|' \
                       r'Finance|Account|Operations|Business|Project|Program|Technical|Research|Security|Network)'

        # Subject patterns (highest confidence)
        subject_patterns = [
            # "Your Job Title Application" or "Your Job Title Remote Application is now..."
            r'[Yy]our\s+([A-Za-z0-9\s\(\)/,\-&]+?' + job_keywords + r'[A-Za-z0-9\s\(\)/,\-&]*?)\s+(?:Remote\s+)?[Aa]pplication',
            # "Your Job Title application" without remote
            r'[Yy]our\s+([A-Za-z0-9\s\-]+?)\s+[Aa]pplication',
            # "Company - Job Title" or "Job Title - Company" or "Subject - Job Title"
            r'-\s+([A-Za-z0-9\s\(\)/,]+?' + job_keywords + r'[A-Za-z0-9\s\(\)/,]*?)$',
            # General "- Something" at end
            r'-\s+([A-Za-z0-9\s\(\)]+?)$',
            # "Position: Job Title"
            r'(?:position|role):\s+(.+?)(?:\s+at|\s+-|$)',
            # "for the Job Title position"
            r'for the\s+(.+?)\s+(?:position|role)',
            # "for Job Title role/position"
            r'for\s+([A-Za-z0-9\s\(\)/,\-&]+?' + job_keywords + r'[A-Za-z0-9\s\(\)/,\-&]*?)\s+(?:position|role|at)',
            # "Job Title position/role"
            r'-\s+(.+?)\s+(?:position|role)',
            # "Thank you for your application - Job Title"
            r'application\s+-\s+(.+?)$',
            # "Application Received - Job Title"
            r'received\s+-\s+(.+?)$',
            # "applying for Job Title"
            r'applying for\s+([A-Za-z0-9\s\(\)/,\-&]+?' + job_keywords + r'[A-Za-z0-9\s\(\)/,\-&]*)',
            # "application for Job Title"
            r'application for\s+([A-Za-z0-9\s\(\)/,\-&]+?' + job_keywords + r'[A-Za-z0-9\s\(\)/,\-&]*)',
            # "Job Title at Company"
            r'^([A-Za-z0-9\s\-]+?' + job_keywords + r'[A-Za-z0-9\s\-]*?)\s+at\s+',
        ]

        for pattern in subject_patterns:
            match = re.search(pattern, subject, re.IGNORECASE)
            if match:
                extracted = match.group(1).strip()
                # Filter out common false positives
                if (len(extracted) > 2 and
                    extracted.lower() not in ['application sent', 'application received', 'online assessment',
                                              'next phase', 'update', 'confirmation', 'complete assessment',
                                              'thank you', 'your application']):
                    job_title = extracted
                    confidence = 0.85
                    break

        # Body patterns (medium-high confidence)
        if not job_title:
            body_patterns = [
                # "role: Job Title" or "position: Job Title"
                r'(?:role|position):\s*([A-Za-z0-9\s\(\),\-&/]+?)[\.\n]',
                # "applying for the Job Title"
                r'applying for (?:the\s+)?([A-Za-z0-9\s\(\),\-&/]+?' + job_keywords + r'[A-Za-z0-9\s\(\),\-&/]*)',
                # "application for the Job Title"
                r'application for (?:the\s+)?([A-Za-z0-9\s\(\),\-&/]+?' + job_keywords + r'[A-Za-z0-9\s\(\),\-&/]*?)(?:\s+position|\s+role|[\.,\n]|$)',
                # "for the Job Title position" in body
                r'for the\s+([A-Za-z0-9\s\(\),\-&/]+?' + job_keywords + r'[A-Za-z0-9\s\(\),\-&/]*?)\s+position',
                # "interest in the Job Title position"
                r'interest in (?:the\s+)?([A-Za-z0-9\s\(\),\-&/]+?)\s+(?:position|role|opportunity)',
                # "for the Job Title position"
                r'for (?:the\s+)?([A-Za-z0-9\s\(\),\-&/]+?)\s+(?:position|role)',
                # "Job Title position at"
                r'([A-Za-z0-9\s\(\),\-&/]+?' + job_keywords + r'[A-Za-z0-9\s\(\),\-&/]*?)\s+(?:position|role)\s+at',
                # "as a/an Job Title"
                r'as an?\s+([A-Za-z0-9\s\(\),\-&/]+?' + job_keywords + r'[A-Za-z0-9\s\(\),\-&/]*)',
                # Just find job title keywords in context
                r'(?:for|the|our|this)\s+([A-Za-z0-9\s\-]+?' + job_keywords + r'[A-Za-z0-9\s\-]*?)(?:\s+position|\s+role|\s+opportunity|[\.,\n])',
                # LinkedIn format: Line with job title
                r'\n\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*?\s+(?:Analyst|Engineer|Manager|Developer|Specialist|Coordinator|Assistant|Intern))\s*\n',
            ]

            for pattern in body_patterns:
                match = re.search(pattern, body, re.IGNORECASE)
                if match:
                    extracted = match.group(1).strip()
                    # Filter out company names and false positives
                    if (len(extracted) > 3 and
                        len(extracted) < 80 and
                        not extracted.startswith('Eleven') and
                        'Recruiting' not in extracted and
                        'Recruitment' not in extracted and
                        'Team' not in extracted and
                        extracted.lower() not in ['los angeles', 'new york', 'san francisco', 'the company']):
                        job_title = extracted
                        confidence = 0.75
                        break

        # Clean up job title
        if job_title:
            # Remove common prefixes/suffixes
            job_title = re.sub(r'\s+(position|role)$', '', job_title, flags=re.IGNORECASE)
            # Remove trailing fragments like "and giving us the", "- Remote", etc.
            job_title = re.sub(r'\s+and\s+.*$', '', job_title, flags=re.IGNORECASE)
            job_title = re.sub(r'\s+-\s*$', '', job_title)
            job_title = re.sub(r'\s+-\s+Remote.*$', '', job_title, flags=re.IGNORECASE)
            # Remove trailing punctuation and whitespace
            job_title = job_title.strip('.,- ')

            # Filter out obvious non-job-titles
            bad_titles = ['default directory', 'email', 'the', 'and', 'your', 'unknown']
            if job_title.lower() in bad_titles:
                job_title = None
                confidence = 0.0

            # Validate: job titles shouldn't be too long or too short
            if job_title and (len(job_title) > 80 or len(job_title) < 3):
                job_title = None
                confidence = 0.0

        return (job_title, confidence) if job_title else (None, 0.0)

    def _extract_location(self, body: str) -> Optional[str]:
        """Extract job location (Remote, City, State, etc.)"""
        # Look for location patterns
        patterns = [
            r'location:\s*(.+?)[\n.]',
            r'based in\s+(.+?)[\n.]',
            r'\((.+?(?:Remote|Hybrid|On-site))\)',
        ]

        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                if len(location) < 100:  # Sanity check
                    return location

        # Look for "Remote" keyword
        if re.search(r'\bremote\b', body, re.IGNORECASE):
            return "Remote"

        return None

    def _detect_action(
        self,
        text: str,
        email_date: Optional[datetime]
    ) -> tuple[bool, Optional[ActionType], Optional[datetime], Optional[str]]:
        """Detect if action is required and classify it"""
        action_required = False
        action_type = None
        deadline = None
        description = None

        # Assessment action
        if any(word in text for word in ['complete the assessment', 'coding challenge', 'take-home']):
            action_required = True
            action_type = ActionType.COMPLETE_ASSESSMENT
            description = "Complete technical assessment"

            # Try to extract deadline
            deadline_match = re.search(r'deadline:?\s*(.+?)[\n.]', text, re.IGNORECASE)
            if deadline_match:
                deadline_str = deadline_match.group(1)
                deadline = self._parse_deadline(deadline_str, email_date)

        # Scheduling action
        elif any(word in text for word in ['schedule', 'select a time', 'availability', 'pick a slot']):
            action_required = True
            action_type = ActionType.SCHEDULE_INTERVIEW
            description = "Schedule interview time"

        # Response needed
        elif any(word in text for word in ['please respond', 'let us know', 'reply with']):
            action_required = True
            action_type = ActionType.RESPOND_TO_EMAIL
            description = "Respond to recruiter"

        # Offer decision
        elif 'offer' in text and any(word in text for word in ['accept', 'decision', 'expire']):
            action_required = True
            action_type = ActionType.ACCEPT_OFFER
            description = "Review and respond to offer"

        return action_required, action_type, deadline, description

    def _parse_deadline(self, deadline_str: str, email_date: Optional[datetime]) -> Optional[datetime]:
        """Parse deadline from text (best effort)"""
        # Try explicit dates
        date_patterns = [
            r'(\d{1,2}/\d{1,2}/\d{4})',  # MM/DD/YYYY
            r'(\w+ \d{1,2}, \d{4})',  # January 15, 2024
        ]

        for pattern in date_patterns:
            match = re.search(pattern, deadline_str)
            if match:
                try:
                    from dateutil import parser
                    return parser.parse(match.group(1))
                except:
                    pass

        # Try relative dates
        if email_date:
            if 'in 3 days' in deadline_str or 'within 3 days' in deadline_str:
                return email_date + timedelta(days=3)
            elif 'in 7 days' in deadline_str or 'within a week' in deadline_str:
                return email_date + timedelta(days=7)

        return None

    def _extract_links(self, body: str) -> List[ExtractedLink]:
        """Extract and classify links from email body"""
        links = []

        # Find all URLs
        url_pattern = r'https?://[^\s<>"\')]+[^\s<>"\'),.]'
        url_matches = re.finditer(url_pattern, body, re.IGNORECASE)

        for match in url_matches:
            url = match.group(0)
            link_type, confidence = self._classify_link(url)

            # Get surrounding text for context
            start = max(0, match.start() - 50)
            end = min(len(body), match.end() + 50)
            context = body[start:end]

            links.append(ExtractedLink(
                url=url,
                link_type=link_type,
                link_text=context,
                confidence=confidence
            ))

        return links

    def _classify_link(self, url: str) -> tuple[LinkType, float]:
        """Classify link type based on domain"""
        url_lower = url.lower()

        # Assessment portals
        for domain, link_type in self.ASSESSMENT_DOMAINS.items():
            if domain in url_lower:
                return (link_type, 0.9)

        # Scheduling links
        for domain, link_type in self.SCHEDULING_DOMAINS.items():
            if domain in url_lower:
                return (link_type, 0.9)

        # Video interview links
        for domain, link_type in self.VIDEO_DOMAINS.items():
            if domain in url_lower:
                return (link_type, 0.9)

        # Job board / ATS
        if any(domain in url_lower for domain in self.ATS_DOMAINS.keys()):
            return (LinkType.COMPANY_PORTAL, 0.8)

        if any(word in url_lower for word in ['jobs', 'careers', 'apply']):
            return (LinkType.JOB_POSTING, 0.6)

        return (LinkType.OTHER, 0.3)

    def _calculate_overall_confidence(self, result: ExtractedData) -> float:
        """Calculate overall confidence score"""
        scores = []

        if result.company_name:
            scores.append(result.company_confidence)

        if result.job_title:
            scores.append(result.job_title_confidence)

        if result.email_type != EmailType.UNKNOWN:
            scores.append(0.7)

        if result.status != ApplicationStatus.OTHER_UPDATE:
            scores.append(0.6)

        if not scores:
            return 0.0

        return sum(scores) / len(scores)

    def _extract_llm_fallback(
        self,
        subject: str,
        body: str,
        from_address: str
    ) -> Optional[ExtractedData]:
        """
        LLM fallback using Groq (Llama 3) for intelligent extraction.
        """
        if not self.llm_client:
            return None

        try:
            import json

            # Truncate body to avoid token limits
            body_truncated = body[:3000] if len(body) > 3000 else body

            prompt = f"""Extract job application information from this email. Return ONLY valid JSON with no other text.

Email Subject: {subject}
From: {from_address}
Body:
{body_truncated}

Return JSON in this exact format:
{{
    "company_name": "Company Name or null if not found",
    "job_title": "Job Title/Position or null if not found",
    "status": "one of: applied, received, interview_scheduled, assessment, rejected, offer, other",
    "action_required": true or false,
    "action_description": "description of action needed or null",
    "is_job_related": true or false
}}

CRITICAL INSTRUCTIONS:
1. COMPANY NAME: Look for unusual/unique words that are NOT common English words - these are likely company names (e.g., "Waymo", "Databricks", "Palantir", "AllCloud"). Company names often look like made-up words or brand names.

2. JOB TITLE: Extract the actual position like "Software Engineer", "Data Analyst", "Data Scientist", "Product Manager", "ML Engineer", etc.
   - If subject says "Your [Job Title] Application" - extract what's between "Your" and "Application"
   - If subject says "Application for [Job Title]" - extract what's after "for"
   - Common titles: Engineer, Analyst, Scientist, Manager, Developer, Designer, Coordinator, Specialist

3. IGNORE these as company names: Gmail, Outlook, Microsoft (unless it's actually a Microsoft job), greenhouse.io, lever.co, workday.com

4. Set is_job_related=false for: security alerts, password resets, account notifications, newsletters, promotional emails

5. Focus on the SUBJECT LINE - it usually contains both company and job title

Return null for fields you truly cannot determine."""

            response = self.llm_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.1
            )
            response_text = response.choices[0].message.content.strip()

            # Try to extract JSON from response
            if response_text.startswith('{'):
                data = json.loads(response_text)
            else:
                # Try to find JSON in response
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    return None

            # Skip non-job-related emails
            if not data.get('is_job_related', True):
                return ExtractedData(
                    company_name=None,
                    job_title=None,
                    status=ApplicationStatus.OTHER_UPDATE,
                    extraction_method="llm_groq_skipped",
                    overall_confidence=0.0
                )

            # Map status string to enum
            status_mapping = {
                'applied': ApplicationStatus.APPLIED_RECEIVED,
                'received': ApplicationStatus.APPLIED_RECEIVED,
                'interview_scheduled': ApplicationStatus.INTERVIEW_SCHEDULED,
                'assessment': ApplicationStatus.NEXT_STEP_ASSESSMENT,
                'rejected': ApplicationStatus.REJECTED,
                'offer': ApplicationStatus.OFFER_EXTENDED,
                'other': ApplicationStatus.OTHER_UPDATE,
            }

            status_str = data.get('status', 'other').lower()
            status = status_mapping.get(status_str, ApplicationStatus.OTHER_UPDATE)

            result = ExtractedData(
                company_name=data.get('company_name') if data.get('company_name') not in [None, 'null', ''] else None,
                job_title=data.get('job_title') if data.get('job_title') not in [None, 'null', ''] else None,
                status=status,
                action_required=data.get('action_required', False),
                action_description=data.get('action_description') if data.get('action_description') not in [None, 'null', ''] else None,
                extraction_method="llm_groq",
                company_confidence=0.9 if data.get('company_name') else 0.0,
                job_title_confidence=0.9 if data.get('job_title') else 0.0,
                overall_confidence=0.9
            )

            return result

        except Exception as e:
            import logging
            logging.error(f"LLM extraction failed: {e}")
            return None


def generate_email_fingerprint(
    original_from: str,
    original_subject: str,
    original_date: Optional[datetime],
    body_prefix: str
) -> str:
    """
    Generate stable fingerprint for email deduplication.

    Args:
        original_from: Sender email
        original_subject: Email subject
        original_date: Send date
        body_prefix: First 500 chars of body

    Returns:
        SHA256 hex digest (64 chars)
    """
    components = [
        original_from or '',
        original_subject or '',
        original_date.isoformat() if original_date else '',
        (body_prefix or '')[:500],
    ]

    fingerprint_input = '|'.join(components).encode('utf-8')
    return hashlib.sha256(fingerprint_input).hexdigest()
