"""
Test Real Email Examples from User

Tests the system with actual job application emails received.
"""

from app.unwrapper import unwrap_forwarded_email
from app.extractor import JobEmailExtractor
from datetime import datetime

print("="*80)
print("TESTING REAL EMAIL SAMPLES")
print("="*80)

extractor = JobEmailExtractor()

# Test Email 1: Eleven Recruiting (Workday notification)
print("\n[EMAIL 1] Eleven Recruiting - Application Sent")
print("-"*80)

email1 = """
Your application was sent to Eleven Recruiting
Eleven Recruiting
Workday Reporting Analyst
Eleven Recruiting · Los Angeles, CA (On-site)
Applied on January 3, 2026
"""

result1 = extractor.extract(
    subject="Your application was sent to Eleven Recruiting",
    body=email1,
    from_address="noreply@linkedin.com",
    date=datetime(2026, 1, 3)
)

print(f"Company: {result1.company_name} (confidence: {result1.company_confidence:.2f})")
print(f"Job Title: {result1.job_title} (confidence: {result1.job_title_confidence:.2f})")
print(f"Status: {result1.status.value}")
print(f"Email Type: {result1.email_type.value}")
print(f"Overall Confidence: {result1.overall_confidence:.2f}")

# Test Email 2: Genworth via Workday
print("\n[EMAIL 2] Genworth - Application Confirmation")
print("-"*80)

email2_subject = "Thank you for your application - Data Analyst"
email2_body = """
Dear Shiven

Thank you very much for your interest in employment opportunities with Genworth and,
specifically, for your application for the Data Analyst position.

Should your application be selected among the most qualified, a Genworth recruiter
will contact you regarding next steps.

If you haven't done so already, please visit Genworth's website, LinkedIn page and
Facebook page to learn more about the meaningful difference our employees make in
the lives of our customers, communities and each other.

Thank you again for your interest in Genworth.

Sincerely,
Genworth Recruitment Services
"""

result2 = extractor.extract(
    subject=email2_subject,
    body=email2_body,
    from_address="gnw@myworkday.com",
    date=datetime(2026, 1, 4)
)

print(f"Company: {result2.company_name} (confidence: {result2.company_confidence:.2f})")
print(f"Job Title: {result2.job_title} (confidence: {result2.job_title_confidence:.2f})")
print(f"Status: {result2.status.value}")
print(f"Email Type: {result2.email_type.value}")
print(f"Overall Confidence: {result2.overall_confidence:.2f}")

# Test Email 3: The Voleon Group
print("\n[EMAIL 3] The Voleon Group - Application Received")
print("-"*80)

email3_subject = "Application Received - Data Analyst"
email3_body = """
Hi Shiven,

Thank you for your interest in The Voleon Group!

We wanted to let you know we received your application for Data Analyst, and we are
delighted that you would consider joining our team.

Our team will review your application and will be in touch if your qualifications
match our needs for the role.

If you are not selected for this position, keep an eye on our jobs page as we're
growing and adding openings.

Thanks again,
The Voleon Group
"""

result3 = extractor.extract(
    subject=email3_subject,
    body=email3_body,
    from_address="careers@voleon.com",
    date=datetime(2026, 1, 5)
)

print(f"Company: {result3.company_name} (confidence: {result3.company_confidence:.2f})")
print(f"Job Title: {result3.job_title} (confidence: {result3.job_title_confidence:.2f})")
print(f"Status: {result3.status.value}")
print(f"Email Type: {result3.email_type.value}")
print(f"Overall Confidence: {result3.overall_confidence:.2f}")

# Test Email 4: CONFLUX SYSTEMS - Rejection
print("\n[EMAIL 4] CONFLUX SYSTEMS - Rejection")
print("-"*80)

email4_subject = "Your update from CONFLUX SYSTEMS"
email4_body = """
Thank you for your interest in the Scientific & Regulatory Affairs position at
CONFLUX SYSTEMS in Atlanta, Georgia, United States.

Unfortunately, we will not be moving forward with your application, but we appreciate
your time and interest in CONFLUX SYSTEMS.

Regards,
CONFLUX SYSTEMS
"""

result4 = extractor.extract(
    subject=email4_subject,
    body=email4_body,
    from_address="noreply@confluxsystems.com",
    date=datetime(2026, 1, 9)
)

print(f"Company: {result4.company_name} (confidence: {result4.company_confidence:.2f})")
print(f"Job Title: {result4.job_title} (confidence: {result4.job_title_confidence:.2f})")
print(f"Status: {result4.status.value}")
print(f"Email Type: {result4.email_type.value}")
print(f"Overall Confidence: {result4.overall_confidence:.2f}")

# Test Email 5: Palo Alto Networks - Rejection
print("\n[EMAIL 5] Palo Alto Networks - Rejection")
print("-"*80)

email5_subject = "Your application to Palo Alto Networks"
email5_body = """
Dear shiven,

Thank you for submitting an application to Palo Alto Networks.

Your background is impressive; however, after careful consideration, we have decided
to pursue other candidates whose skills and experience are more aligned with the
requirements for this particular role: IT Principal AI Engineer.

Based on your consent selection, we may keep your application on file for future
opportunities and encourage you to continue to review our Careers page for other
openings that may suit your background.

Thank you for your interest in Palo Alto Networks and good luck in your career search.

Sincerely,
The Palo Alto Networks Recruiting Team
"""

result5 = extractor.extract(
    subject=email5_subject,
    body=email5_body,
    from_address="recruiting@paloaltonetworks.com",
    date=datetime(2026, 1, 10)
)

print(f"Company: {result5.company_name} (confidence: {result5.company_confidence:.2f})")
print(f"Job Title: {result5.job_title} (confidence: {result5.job_title_confidence:.2f})")
print(f"Status: {result5.status.value}")
print(f"Email Type: {result5.email_type.value}")
print(f"Overall Confidence: {result5.overall_confidence:.2f}")

# Test Email 6: Assessment Invite
print("\n[EMAIL 6] Assessment Invite")
print("-"*80)

email6_subject = "Next Phase - Complete Assessment"
email6_body = """
Dear Shiven,

Congratulations, you've been moved to the next phase of our hiring process!

Our next step requires that you complete an assessment. To complete the assessment,
please click on the link or button below.

When registering for the assessment, please be sure that you use the same email
address you used when applying for this job.

Please note the following:
Complete the assessment in a quiet place, free from interruption, and in ONE session.
This assessment typically takes about 40 minutes.

Thank you and good luck!

https://hrfuse.applicantpro.com/apply/apis/hrfuse_proxy.php?application_id=137528388

Sincerely,
Human Resources
"""

result6 = extractor.extract(
    subject=email6_subject,
    body=email6_body,
    from_address="noreply@applicantpro.com",
    date=datetime(2026, 1, 11)
)

print(f"Company: {result6.company_name} (confidence: {result6.company_confidence:.2f})")
print(f"Job Title: {result6.job_title} (confidence: {result6.job_title_confidence:.2f})")
print(f"Status: {result6.status.value}")
print(f"Email Type: {result6.email_type.value}")
print(f"Action Required: {result6.action_required}")
print(f"Action Type: {result6.action_type.value if result6.action_type else 'None'}")
print(f"Links Found: {len(result6.links)}")
if result6.links:
    for link in result6.links:
        print(f"  - {link.link_type.value}: {link.url[:50]}...")
print(f"Overall Confidence: {result6.overall_confidence:.2f}")

# Test Email 7: ByteDance CodeSignal
print("\n[EMAIL 7] ByteDance - CodeSignal Assessment")
print("-"*80)

email7_subject = "ByteDance Online Assessment - Software Engineer Intern"
email7_body = """
Hey Shiven Paudyal,

Thanks for submitting your application to ByteDance Early Careers positions for 2026!

You're invited to take our online assessment for Software Engineer Intern
(Applied Machine Learning - ML System) - 2026 Summer (BS/MS), administered by
CodeSignal, which is required in order to move forward in the overall assessment process.

This is a technical evaluation to help us assess your skills in basic coding,
implementation, data structures, and problem solving.

You will have only one attempt to take the assessment, so we encourage you to prepare
in advance by reviewing the Test-taker FAQs, CodeSignal Privacy Policy, and practice
questions before getting started.
"""

result7 = extractor.extract(
    subject=email7_subject,
    body=email7_body,
    from_address="recruiting@bytedance.com",
    date=datetime(2026, 1, 12)
)

print(f"Company: {result7.company_name} (confidence: {result7.company_confidence:.2f})")
print(f"Job Title: {result7.job_title} (confidence: {result7.job_title_confidence:.2f})")
print(f"Status: {result7.status.value}")
print(f"Email Type: {result7.email_type.value}")
print(f"Action Required: {result7.action_required}")
print(f"Action Type: {result7.action_type.value if result7.action_type else 'None'}")
print(f"Overall Confidence: {result7.overall_confidence:.2f}")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)

emails = [result1, result2, result3, result4, result5, result6, result7]
avg_confidence = sum(e.overall_confidence for e in emails) / len(emails)

print(f"\nTotal Emails Tested: {len(emails)}")
print(f"Average Confidence: {avg_confidence:.2f}")

companies_found = sum(1 for e in emails if e.company_name)
jobs_found = sum(1 for e in emails if e.job_title)

print(f"Companies Extracted: {companies_found}/{len(emails)} ({companies_found/len(emails)*100:.0f}%)")
print(f"Job Titles Extracted: {jobs_found}/{len(emails)} ({jobs_found/len(emails)*100:.0f}%)")

print("\nPattern Improvements Needed:")
if avg_confidence < 0.7:
    print("- Tune company extraction patterns")
if jobs_found < len(emails):
    print("- Improve job title extraction")

print("="*80)
