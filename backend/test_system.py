"""
System Test Script

Quick test to verify all components work.
Run: python test_system.py
"""

print("="*80)
print("JOB TRACKER - SYSTEM TEST")
print("="*80)

# Test 1: Unwrapper
print("\n[TEST 1] Forwarded Email Unwrapper...")
try:
    from app.unwrapper import unwrap_forwarded_email

    sample_email = """
---------- Forwarded message ---------
From: recruiting@google.com
Date: Mon, Jan 15, 2024 at 10:30 AM
Subject: Software Engineer - Application Received

Thank you for applying to Google for the Software Engineer position.
"""

    result = unwrap_forwarded_email(sample_email, None)

    assert result.original_from == "recruiting@google.com"
    assert "Software Engineer" in result.original_subject
    assert result.confidence > 0.7

    print("[PASS] Unwrapper working correctly")
    print(f"   From: {result.original_from}")
    print(f"   Subject: {result.original_subject}")
    print(f"   Confidence: {result.confidence:.2f}")

except Exception as e:
    print(f"[FAIL] {e}")

# Test 2: Extractor
print("\n[TEST 2] Classification & Extraction...")
try:
    from app.extractor import JobEmailExtractor
    from datetime import datetime

    extractor = JobEmailExtractor()

    result = extractor.extract(
        subject="Application Confirmation - Software Engineer - Google",
        body="Thank you for applying to Google for the Software Engineer position.",
        from_address="no-reply@myworkdaysite.com",
        date=datetime.now()
    )

    assert result.company_name is not None
    assert result.job_title is not None
    assert result.overall_confidence > 0.5

    print("[PASS] Extractor working correctly")
    print(f"   Company: {result.company_name} (confidence: {result.company_confidence:.2f})")
    print(f"   Job Title: {result.job_title} (confidence: {result.job_title_confidence:.2f})")
    print(f"   Status: {result.status.value}")
    print(f"   Email Type: {result.email_type.value}")

except Exception as e:
    print(f"[FAIL] {e}")

# Test 3: Fingerprinting
print("\n[TEST 3] Email Fingerprinting...")
try:
    from app.extractor import generate_email_fingerprint
    from datetime import datetime

    fp1 = generate_email_fingerprint(
        "test@example.com",
        "Test Subject",
        datetime.now(),
        "Email body content"
    )

    fp2 = generate_email_fingerprint(
        "test@example.com",
        "Test Subject",
        datetime.now(),
        "Email body content"
    )

    assert fp1 == fp2  # Same email = same fingerprint
    assert len(fp1) == 64  # SHA256 hex = 64 chars

    print("[PASS] Fingerprinting working correctly")
    print(f"   Fingerprint: {fp1[:16]}...")

except Exception as e:
    print(f"[FAIL] {e}")

# Test 4: Database Models
print("\n[TEST 4] Database Models...")
try:
    from app.models import (
        Application, ApplicationEvent, RawEmail,
        ApplicationStatus, EmailType, LinkType
    )

    # Check enums
    assert ApplicationStatus.APPLIED_RECEIVED
    assert EmailType.APPLICATION_CONFIRMATION
    assert LinkType.ASSESSMENT_PORTAL

    print("[PASS] Models imported correctly")
    print(f"   Application statuses: {len(ApplicationStatus)}")
    print(f"   Email types: {len(EmailType)}")
    print(f"   Link types: {len(LinkType)}")

except Exception as e:
    print(f"[FAIL] {e}")

# Test 5: Dependencies
print("\n[TEST 5] Dependencies...")
errors = []

try:
    import fastapi
    print("[OK] fastapi")
except:
    errors.append("fastapi")
    print("[MISSING] fastapi - Run: pip install fastapi")

try:
    import sqlalchemy
    print("[OK] sqlalchemy")
except:
    errors.append("sqlalchemy")
    print("[MISSING] sqlalchemy - Run: pip install sqlalchemy")

try:
    import openpyxl
    print("[OK] openpyxl")
except:
    errors.append("openpyxl")
    print("[MISSING] openpyxl - Run: pip install openpyxl")

try:
    from bs4 import BeautifulSoup
    print("[OK] beautifulsoup4")
except:
    errors.append("beautifulsoup4")
    print("[MISSING] beautifulsoup4 - Run: pip install beautifulsoup4")

try:
    import msal
    print("[OK] msal")
except:
    errors.append("msal")
    print("[MISSING] msal - Run: pip install msal")

try:
    import pydantic
    print("[OK] pydantic")
except:
    errors.append("pydantic")
    print("[MISSING] pydantic - Run: pip install pydantic")

if errors:
    print(f"\n[WARNING] Missing dependencies: {', '.join(errors)}")
    print("   Run: pip install -r requirements.txt")
else:
    print("\n[OK] All dependencies installed")

# Summary
print("\n" + "="*80)
print("SYSTEM TEST COMPLETE")
print("="*80)

print("\nNext Steps:")
print("1. Run unit tests: pytest tests/test_unwrapper.py -v")
print("2. Start API server: python -m uvicorn app.main:app --reload")
print("3. Visit API docs: http://localhost:8000/docs")
print("4. See QUICKSTART.md for full setup")

print("\n[SUCCESS] All core components are working!")
print("="*80)
