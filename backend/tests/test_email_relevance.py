"""Guardrails for conflicting email relevance and extraction confidence."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.extractor import JobEmailExtractor, ExtractedData
from app.models import EmailType, ApplicationStatus


def _result(confidence, email_type=EmailType.UNKNOWN, company=None):
    return ExtractedData(
        overall_confidence=confidence,
        email_type=email_type,
        company_name=company,
        status=ApplicationStatus.OTHER_UPDATE,
    )


def test_llm_unrelated_with_rule_signal_is_sent_to_manual_review(monkeypatch):
    extractor = JobEmailExtractor(llm_client=object())
    rule = _result(0.7, EmailType.GENERAL_UPDATE, "ExampleCo")
    llm = ExtractedData(
        is_job_related=False, overall_confidence=0.0,
        extraction_method="llm_groq_skipped",
    )
    monkeypatch.setattr(extractor, "_extract_rule_based", lambda *args: rule)
    monkeypatch.setattr(extractor, "_extract_llm_fallback", lambda *args: llm)
    result = extractor.extract("ExampleCo update", "Hello", "someone@example.com")
    assert result.needs_manual_review is True
    assert result.extraction_method == "rule_llm_relevance_conflict"
    assert result.is_job_related is None


def test_llm_unrelated_without_rule_signal_is_ignored(monkeypatch):
    extractor = JobEmailExtractor(llm_client=object())
    rule = _result(0.0)
    llm = ExtractedData(
        is_job_related=False, overall_confidence=0.0,
        extraction_method="llm_groq_skipped",
    )
    monkeypatch.setattr(extractor, "_extract_rule_based", lambda *args: rule)
    monkeypatch.setattr(extractor, "_extract_llm_fallback", lambda *args: llm)
    result = extractor.extract("Security alert", "Password reset", "notice@example.com")
    assert result.is_job_related is False
    assert result.needs_manual_review is False


def test_positive_llm_can_replace_low_rule_confidence(monkeypatch):
    extractor = JobEmailExtractor(llm_client=object())
    rule = _result(0.4)
    llm = ExtractedData(
        is_job_related=True, company_name="ExampleCo",
        overall_confidence=0.9, extraction_method="llm_groq",
    )
    monkeypatch.setattr(extractor, "_extract_rule_based", lambda *args: rule)
    monkeypatch.setattr(extractor, "_extract_llm_fallback", lambda *args: llm)
    result = extractor.extract("Application", "Thanks", "jobs@example.com")
    assert result.company_name == "ExampleCo"
    assert result.is_job_related is True


def test_no_llm_answer_keeps_rule_result(monkeypatch):
    extractor = JobEmailExtractor(llm_client=object())
    rule = _result(0.6)
    monkeypatch.setattr(extractor, "_extract_rule_based", lambda *args: rule)
    monkeypatch.setattr(extractor, "_extract_llm_fallback", lambda *args: None)
    assert extractor.extract("Subject", "Body", "jobs@example.com") is rule
