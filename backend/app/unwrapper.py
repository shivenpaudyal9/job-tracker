"""
Forwarded Email Unwrapper

Critical component that extracts original email content from Gmail→Outlook forwards.

Handles:
- Gmail forward format ("---------- Forwarded message ---------")
- Outlook forward format ("From:", "Sent:", "To:", "Subject:")
- Both HTML and plain text
- Strips quoted replies and signatures
"""

import re
from datetime import datetime
from typing import Optional, Tuple
from dataclasses import dataclass
from bs4 import BeautifulSoup
import email.utils


@dataclass
class UnwrappedEmail:
    """Result of unwrapping a forwarded email"""
    original_from: Optional[str]
    original_to: Optional[str]
    original_subject: Optional[str]
    original_date: Optional[datetime]
    clean_body_text: Optional[str]
    clean_body_html: Optional[str]
    confidence: float  # 0.0-1.0
    method_used: str  # Description of unwrapping method


class ForwardedEmailUnwrapper:
    """
    Detects and unwraps forwarded emails to extract original content.

    Strategy:
    1. Detect forward patterns in text/HTML
    2. Extract original headers (From, To, Subject, Date)
    3. Extract clean body (remove forward headers, signatures, quoted replies)
    4. Calculate confidence based on pattern matches
    """

    # Gmail forward patterns
    GMAIL_FORWARD_MARKERS = [
        r'---------- Forwarded message ---------',
        r'Begin forwarded message:',
        r'Forwarded message',
    ]

    # Outlook/Exchange forward patterns
    OUTLOOK_FORWARD_MARKERS = [
        r'From:.*Sent:.*To:.*Subject:',
        r'________________________________',
    ]

    # Header patterns
    HEADER_PATTERNS = {
        'from': [
            r'From:\s*(.+?)(?:\n|<br|$)',
            r'From:\s*<([^>]+)>',
            r'From:\s*(.+?)\s*<',
        ],
        'to': [
            r'To:\s*(.+?)(?:\n|<br|$)',
            r'To:\s*<([^>]+)>',
        ],
        'subject': [
            r'Subject:\s*(.+?)(?:\n|<br|$)',
        ],
        'date': [
            r'Date:\s*(.+?)(?:\n|<br|$)',
            r'Sent:\s*(.+?)(?:\n|<br|$)',
        ],
    }

    # Signature patterns to strip
    SIGNATURE_PATTERNS = [
        r'\n--\s*\n',  # Standard email signature delimiter
        r'\nBest regards,?\n',
        r'\nThanks,?\n',
        r'\nRegards,?\n',
        r'\nSent from my iPhone',
        r'\nSent from my Android',
        r'\nGet Outlook for iOS',
    ]

    # Quote patterns to strip
    QUOTE_PATTERNS = [
        r'On .+? wrote:',
        r'>\s*>',  # Multiple levels of quoting
    ]

    def unwrap(self, body_text: Optional[str], body_html: Optional[str]) -> UnwrappedEmail:
        """
        Main entry point: unwrap forwarded email from text or HTML body.

        Args:
            body_text: Plain text email body
            body_html: HTML email body

        Returns:
            UnwrappedEmail with extracted fields and confidence score
        """
        # Try HTML first (more structured)
        if body_html:
            result = self._unwrap_html(body_html)
            if result.confidence > 0.6:
                return result

        # Fall back to plain text
        if body_text:
            result = self._unwrap_text(body_text)
            if result.confidence > 0.0:
                return result

        # No forwarding detected - return original
        return UnwrappedEmail(
            original_from=None,
            original_to=None,
            original_subject=None,
            original_date=None,
            clean_body_text=body_text,
            clean_body_html=body_html,
            confidence=1.0,  # High confidence it's NOT forwarded
            method_used="no_forwarding_detected"
        )

    def _unwrap_html(self, html: str) -> UnwrappedEmail:
        """Unwrap forwarded email from HTML body"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            text = soup.get_text('\n')

            # Try to detect forward block
            forward_match = None
            for pattern in self.GMAIL_FORWARD_MARKERS + self.OUTLOOK_FORWARD_MARKERS:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    forward_match = match
                    break

            if not forward_match:
                return UnwrappedEmail(None, None, None, None, None, html, 0.0, "no_html_forward_detected")

            # Extract text after forward marker
            forwarded_content = text[forward_match.end():]

            # Extract headers
            original_from = self._extract_header(forwarded_content, 'from')
            original_to = self._extract_header(forwarded_content, 'to')
            original_subject = self._extract_header(forwarded_content, 'subject')
            original_date_str = self._extract_header(forwarded_content, 'date')
            original_date = self._parse_date(original_date_str) if original_date_str else None

            # Extract clean body (after headers)
            clean_body = self._extract_clean_body(forwarded_content)

            # Calculate confidence
            confidence = self._calculate_confidence(
                original_from, original_subject, original_date, clean_body
            )

            return UnwrappedEmail(
                original_from=original_from,
                original_to=original_to,
                original_subject=original_subject,
                original_date=original_date,
                clean_body_text=clean_body,
                clean_body_html=None,  # Would need more complex HTML parsing
                confidence=confidence,
                method_used="html_forward_extraction"
            )

        except Exception as e:
            return UnwrappedEmail(None, None, None, None, None, html, 0.0, f"html_error: {str(e)}")

    def _unwrap_text(self, text: str) -> UnwrappedEmail:
        """Unwrap forwarded email from plain text body"""
        # Detect forward marker
        forward_match = None
        for pattern in self.GMAIL_FORWARD_MARKERS + self.OUTLOOK_FORWARD_MARKERS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                forward_match = match
                break

        if not forward_match:
            return UnwrappedEmail(None, None, None, None, text, None, 0.0, "no_text_forward_detected")

        # Extract forwarded content
        forwarded_content = text[forward_match.end():]

        # Extract headers
        original_from = self._extract_header(forwarded_content, 'from')
        original_to = self._extract_header(forwarded_content, 'to')
        original_subject = self._extract_header(forwarded_content, 'subject')
        original_date_str = self._extract_header(forwarded_content, 'date')
        original_date = self._parse_date(original_date_str) if original_date_str else None

        # Extract clean body
        clean_body = self._extract_clean_body(forwarded_content)

        # Calculate confidence
        confidence = self._calculate_confidence(
            original_from, original_subject, original_date, clean_body
        )

        return UnwrappedEmail(
            original_from=original_from,
            original_to=original_to,
            original_subject=original_subject,
            original_date=original_date,
            clean_body_text=clean_body,
            clean_body_html=None,
            confidence=confidence,
            method_used="text_forward_extraction"
        )

    def _extract_header(self, content: str, header_type: str) -> Optional[str]:
        """Extract a specific header from forwarded content"""
        patterns = self.HEADER_PATTERNS.get(header_type, [])

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1).strip()
                # Clean HTML tags if present
                value = re.sub(r'<[^>]+>', '', value)
                return value if value else None

        return None

    def _extract_clean_body(self, content: str) -> str:
        """
        Extract clean email body, removing:
        - Forward headers
        - Signatures
        - Quoted replies
        """
        # Find where the headers end (after Subject: line typically)
        header_end = 0
        for header in ['From:', 'To:', 'Subject:', 'Date:', 'Sent:']:
            match = re.search(f'{header}.*?\\n', content, re.IGNORECASE)
            if match:
                header_end = max(header_end, match.end())

        # Start body after headers
        body = content[header_end:].strip()

        # Remove signatures
        for pattern in self.SIGNATURE_PATTERNS:
            body = re.split(pattern, body, maxsplit=1)[0]

        # Remove quoted replies
        for pattern in self.QUOTE_PATTERNS:
            body = re.split(pattern, body, maxsplit=1)[0]

        # Clean up whitespace
        body = re.sub(r'\n{3,}', '\n\n', body)  # Max 2 consecutive newlines
        body = body.strip()

        return body

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats from email headers"""
        if not date_str:
            return None

        try:
            # Try email.utils first (RFC 2822 format)
            tuple_time = email.utils.parsedate_tz(date_str)
            if tuple_time:
                return datetime(*tuple_time[:6])
        except:
            pass

        # Try common formats
        formats = [
            '%a, %d %b %Y %H:%M:%S %z',  # Mon, 01 Jan 2024 10:30:00 +0000
            '%d %b %Y %H:%M:%S',  # 01 Jan 2024 10:30:00
            '%m/%d/%Y %I:%M %p',  # 01/15/2024 10:30 AM
            '%Y-%m-%d %H:%M:%S',  # 2024-01-15 10:30:00
        ]

        for fmt in formats:
            try:
                # Remove timezone info if present (simplification)
                clean_date = re.sub(r'\s*[+-]\d{4}$', '', date_str.strip())
                return datetime.strptime(clean_date, fmt.replace(' %z', ''))
            except:
                continue

        return None

    def _calculate_confidence(
        self,
        original_from: Optional[str],
        original_subject: Optional[str],
        original_date: Optional[datetime],
        clean_body: Optional[str]
    ) -> float:
        """
        Calculate confidence score for unwrapping.

        High confidence if we extracted multiple headers successfully.
        """
        score = 0.0

        if original_from and '@' in original_from:
            score += 0.35
        if original_subject and len(original_subject) > 3:
            score += 0.25
        if original_date:
            score += 0.20
        if clean_body and len(clean_body) > 50:
            score += 0.20

        return min(score, 1.0)


# Convenience function
def unwrap_forwarded_email(body_text: Optional[str], body_html: Optional[str]) -> UnwrappedEmail:
    """
    Convenience function to unwrap a forwarded email.

    Usage:
        result = unwrap_forwarded_email(email.body_text, email.body_html)
        if result.confidence > 0.7:
            # Use unwrapped data
            print(f"Original from: {result.original_from}")
            print(f"Subject: {result.original_subject}")
    """
    unwrapper = ForwardedEmailUnwrapper()
    return unwrapper.unwrap(body_text, body_html)
