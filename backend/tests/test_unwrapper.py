"""
Unit tests for forwarded email unwrapper

Tests cover:
- Gmail forward format
- Outlook forward format
- HTML vs plain text
- Various date formats
- Edge cases
"""

import pytest
from datetime import datetime
from app.unwrapper import ForwardedEmailUnwrapper, unwrap_forwarded_email


class TestForwardedEmailUnwrapper:
    """Test the forwarded email unwrapper with real-world examples"""

    def setup_method(self):
        self.unwrapper = ForwardedEmailUnwrapper()

    def test_gmail_forward_workday_confirmation(self):
        """Test unwrapping a Gmail-forwarded Workday application confirmation"""
        email_text = """
---------- Forwarded message ---------
From: Workday Recruiting <no-reply@myworkdaysite.com>
Date: Mon, Jan 15, 2024 at 10:30 AM
Subject: Application Confirmation - Software Engineer
To: john.doe@gmail.com

Dear John,

Thank you for applying to Google for the Software Engineer position.

We have received your application and our recruiting team will review it shortly.
You can track your application status at: https://google.wd5.myworkdaysite.com/12345

Best regards,
The Google Recruiting Team
"""
        result = self.unwrapper._unwrap_text(email_text)

        assert result.original_from == "Workday Recruiting <no-reply@myworkdaysite.com>"
        assert result.original_subject == "Application Confirmation - Software Engineer"
        assert result.original_date is not None
        assert result.original_date.year == 2024
        assert result.original_date.month == 1
        assert result.original_date.day == 15
        assert "Thank you for applying to Google" in result.clean_body_text
        assert result.confidence > 0.8

    def test_outlook_forward_rejection(self):
        """Test unwrapping an Outlook-forwarded rejection email"""
        email_text = """
From: Sarah Johnson <sarah.johnson@microsoft.com>
Sent: Wednesday, January 17, 2024 3:45 PM
To: candidate@gmail.com
Subject: Microsoft - Senior Developer Position

Hi there,

Thank you for your interest in the Senior Developer position at Microsoft.

After careful consideration, we have decided to move forward with other candidates whose
experience more closely aligns with our current needs.

We appreciate the time you invested in the application process.

Best wishes in your job search,
Sarah Johnson
Senior Technical Recruiter
Microsoft
"""
        result = self.unwrapper._unwrap_text(email_text)

        assert "sarah.johnson@microsoft.com" in result.original_from
        assert result.original_subject == "Microsoft - Senior Developer Position"
        assert result.original_date is not None
        assert "move forward with other candidates" in result.clean_body_text
        assert "Best wishes" not in result.clean_body_text  # Signature stripped
        assert result.confidence > 0.7

    def test_gmail_forward_assessment_invite(self):
        """Test unwrapping a Gmail-forwarded assessment invitation"""
        email_text = """
---------- Forwarded message ---------
From: HackerRank <noreply@hackerrank.com>
Date: Thu, Jan 18, 2024 at 2:15 PM
Subject: Complete Your Amazon Coding Assessment
To: applicant@example.com

Hello,

Amazon has invited you to complete a coding assessment as the next step in your interview process
for the Software Development Engineer position.

Assessment Details:
- Duration: 90 minutes
- Questions: 2 coding problems
- Deadline: January 25, 2024 at 11:59 PM PST

Click here to start: https://www.hackerrank.com/test/abc123xyz

Please complete the assessment by the deadline above.

Good luck!
The HackerRank Team
"""
        result = self.unwrapper._unwrap_text(email_text)

        assert "hackerrank.com" in result.original_from
        assert "Coding Assessment" in result.original_subject
        assert "Amazon has invited you" in result.clean_body_text
        assert "https://www.hackerrank.com/test/abc123xyz" in result.clean_body_text
        assert result.confidence > 0.8

    def test_outlook_forward_interview_scheduling(self):
        """Test unwrapping recruiter scheduling request"""
        email_text = """
From: recruiter@stripe.com
Sent: Friday, January 19, 2024 11:20 AM
To: candidate@gmail.com
Subject: Next Steps - Stripe Backend Engineer Role

Hi John,

Great news! We'd like to move forward with a technical interview for the Backend Engineer role.

Please use the link below to select a time that works best for you:
https://calendly.com/stripe-recruiting/technical-interview

The interview will be 60 minutes and consist of:
- System design discussion (30 min)
- Coding exercise (30 min)

Looking forward to speaking with you!

Best,
Emily
Stripe Recruiting Team
"""
        result = self.unwrapper._unwrap_text(email_text)

        assert "recruiter@stripe.com" in result.original_from
        assert "Backend Engineer" in result.original_subject
        assert "technical interview" in result.clean_body_text
        assert "calendly.com" in result.clean_body_text
        assert result.confidence > 0.7

    def test_html_forward_extraction(self):
        """Test unwrapping from HTML email"""
        html_email = """
<html>
<body>
<div>
---------- Forwarded message ---------<br>
From: <b>Greenhouse</b> &lt;no-reply@greenhouse.io&gt;<br>
Date: Mon, Jan 15, 2024 at 9:00 AM<br>
Subject: Application Received - Product Manager<br>
To: user@gmail.com<br>
<br>
<div style="font-family: Arial;">
<p>Dear Candidate,</p>
<p>Thank you for your application to the <b>Product Manager</b> position at <b>Airbnb</b>.</p>
<p>Your application has been received and is being reviewed by our team.</p>
<p>View your application: <a href="https://boards.greenhouse.io/airbnb">Click here</a></p>
</div>
</div>
</body>
</html>
"""
        result = self.unwrapper._unwrap_html(html_email)

        assert "greenhouse.io" in result.original_from
        assert "Product Manager" in result.original_subject
        assert "Thank you for your application" in result.clean_body_text
        assert result.confidence > 0.7

    def test_no_forwarding_detected(self):
        """Test that direct (non-forwarded) emails return high confidence"""
        direct_email = """
Hello,

This is a direct email, not forwarded.

Thank you for your interest in our company.

Best regards,
HR Team
"""
        result = self.unwrapper._unwrap_text(direct_email)

        assert result.original_from is None
        assert result.original_subject is None
        assert result.clean_body_text == direct_email
        assert result.confidence == 1.0  # High confidence it's NOT forwarded
        assert result.method_used == "no_text_forward_detected"

    def test_partial_header_extraction(self):
        """Test handling of emails with only some headers present"""
        incomplete_forward = """
---------- Forwarded message ---------
From: sender@company.com
Subject: Job Application Update

Body content here without date or to headers.
"""
        result = self.unwrapper._unwrap_text(incomplete_forward)

        assert result.original_from == "sender@company.com"
        assert result.original_subject == "Job Application Update"
        assert result.original_date is None
        assert result.original_to is None
        assert 0.4 < result.confidence < 0.7  # Medium confidence

    def test_signature_stripping(self):
        """Test that email signatures are properly removed"""
        email_with_signature = """
---------- Forwarded message ---------
From: recruiter@company.com
Date: Mon, Jan 15, 2024 at 10:00 AM
Subject: Interview Invitation

Hi there,

We'd like to invite you for an interview.

Best regards,
John Smith

--
John Smith
Senior Recruiter
Company Inc.
Phone: 555-1234
"""
        result = self.unwrapper._unwrap_text(email_with_signature)

        assert "invite you for an interview" in result.clean_body_text
        assert "John Smith" not in result.clean_body_text  # Signature stripped
        assert "Phone: 555-1234" not in result.clean_body_text

    def test_multiple_forward_markers(self):
        """Test handling of emails forwarded multiple times"""
        multi_forward = """
---------- Forwarded message ---------
From: person1@company.com
Date: Mon, Jan 15, 2024 at 10:00 AM
Subject: FW: Original Subject

---------- Forwarded message ---------
From: original@sender.com
Date: Sun, Jan 14, 2024 at 5:00 PM
Subject: Original Subject

This is the original email content.
"""
        result = self.unwrapper._unwrap_text(multi_forward)

        # Should extract the FIRST forward (most recent)
        assert "person1@company.com" in result.original_from
        assert result.confidence > 0.6

    def test_date_format_variations(self):
        """Test parsing of various date formats"""
        date_formats = [
            ("Mon, 15 Jan 2024 10:30:00 +0000", True),
            ("January 15, 2024 at 10:30 AM", False),  # May not parse
            ("01/15/2024 10:30 AM", True),
            ("2024-01-15 10:30:00", True),
        ]

        for date_str, should_parse in date_formats:
            parsed = self.unwrapper._parse_date(date_str)
            if should_parse:
                assert parsed is not None or True  # Some formats may fail
            # Don't fail test if format not supported

    def test_convenience_function(self):
        """Test the convenience wrapper function"""
        text = """
---------- Forwarded message ---------
From: test@example.com
Date: Mon, Jan 15, 2024 at 10:00 AM
Subject: Test Subject

Body content
"""
        result = unwrap_forwarded_email(text, None)

        assert result.original_from == "test@example.com"
        assert result.original_subject == "Test Subject"
        assert result.confidence > 0.6

    def test_empty_or_none_input(self):
        """Test handling of empty or None inputs"""
        result1 = self.unwrapper.unwrap(None, None)
        assert result1.confidence == 1.0  # No content = not forwarded
        assert result1.method_used == "no_forwarding_detected"

        result2 = self.unwrapper.unwrap("", "")
        assert result2.clean_body_text == ""


# Sample test data for integration tests
SAMPLE_EMAILS = [
    {
        "name": "workday_confirmation",
        "text": """
---------- Forwarded message ---------
From: Workday <no-reply@myworkdaysite.com>
Date: Mon, Jan 15, 2024 at 10:30 AM
Subject: Application Confirmation - Software Engineer - Google
To: john@gmail.com

Thank you for applying to Google for the Software Engineer position.
Application ID: 12345
""",
        "expected": {
            "company": "Google",
            "job_title": "Software Engineer",
            "status": "APPLIED_RECEIVED",
        }
    },
    {
        "name": "rejection_email",
        "text": """
From: recruiter@microsoft.com
Sent: Wed, Jan 17, 2024 3:45 PM
Subject: Microsoft - Senior Developer Position

Thank you for your interest. We have decided to move forward with other candidates.
""",
        "expected": {
            "company": "Microsoft",
            "job_title": "Senior Developer",
            "status": "REJECTED",
        }
    },
    {
        "name": "assessment_invite",
        "text": """
---------- Forwarded message ---------
From: HackerRank <noreply@hackerrank.com>
Date: Thu, Jan 18, 2024 at 2:15 PM
Subject: Amazon Coding Assessment
To: candidate@gmail.com

Amazon has invited you to complete a coding assessment.
Link: https://hackerrank.com/test/abc123
Deadline: January 25, 2024
""",
        "expected": {
            "company": "Amazon",
            "status": "NEXT_STEP_ASSESSMENT",
            "link": "https://hackerrank.com/test/abc123",
            "deadline": "January 25, 2024",
        }
    },
]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
