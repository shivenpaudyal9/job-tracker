"""Regression tests for evidence-gated LLM extraction and safe routing."""
import json
from datetime import datetime
from types import SimpleNamespace

from app.extractor import JobEmailExtractor
from app.llm_validation import validate_llm_payload
from app.matcher import ApplicationMatcher
from app.models import ApplicationStatus


SUBJECT = "Amazon Software Engineer application"
BODY = "Thank you for applying to Amazon for the Software Engineer position. Please complete your coding assessment."
SENDER = "recruiting@amazon.com"


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


def test_rejects_ungrounded_hallucinated_company():
    payload = good_payload()
    payload["company_name"] = "Microsoft"
    assert validate_llm_payload(payload, SUBJECT, BODY, SENDER) is None


def test_rejects_invalid_status_or_unrelated_emails():
    payload = good_payload()
    payload["status"] = "hired"
    assert validate_llm_payload(payload, SUBJECT, BODY, SENDER) is None
    payload = good_payload()
    payload["is_job_related"] = False
    assert validate_llm_payload(payload, SUBJECT, BODY, SENDER) is None


def test_rejects_missing_or_fabricated_status_evidence():
    payload = good_payload()
    del payload["status_evidence"]
    assert validate_llm_payload(payload, SUBJECT, BODY, SENDER) is None
    payload = good_payload()
    payload["status_evidence"] = "Congratulations, you're hired"
    assert validate_llm_payload(payload, SUBJECT, BODY, SENDER) is None


def test_rejects_unsupported_action():
    payload = good_payload()
    payload["action_evidence"] = "send us your bank password"
    assert validate_llm_payload(payload, SUBJECT, BODY, SENDER) is None


def test_grounded_output_has_quality_score_not_fixed_llm_confidence():
    payload = good_payload()
    a = validate_llm_payload(payload, SUBJECT, BODY, SENDER)
    assert a is not None and 0 < a["evidence_quality"] <= 1
    payload["action_required"] = False
    payload["action_description"] = None
    payload["action_evidence"] = None
    b = validate_llm_payload(payload, SUBJECT, BODY, SENDER)
    assert b is not None and b["evidence_quality"] < a["evidence_quality"]


def test_status_disagreement_routes_to_review_before_database_match():
    extractor = JobEmailExtractor(llm_client=FakeGroq(good_payload()))
    result = extractor.extract(SUBJECT, BODY, SENDER, datetime(2026, 10, 29))
    assert result.status == ApplicationStatus.NEXT_STEP_ASSESSMENT
    assert result.requires_manual_review
    matcher = ApplicationMatcher(db=None, user_id=1)
    matched = matcher.match(result, datetime(2026, 10, 29))
    assert matched.should_review is True
    assert matched.match_type == "llm_status_disagreement"


def test_invalid_llm_response_keeps_rule_based_result():
    payload = good_payload()
    payload["status_evidence"] = "nonexistent quote in email"
    extractor = JobEmailExtractor(llm_client=FakeGroq(payload))
    result = extractor.extract(SUBJECT, BODY, SENDER, datetime(2026, 10, 29))
    assert result.extraction_method == "rule_based"
    assert result.requires_manual_review is False
