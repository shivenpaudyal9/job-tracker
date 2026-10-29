"""Offline evaluation reports automation coverage and precision on labeled records."""
from scripts.evaluate_llm_policy import evaluate
from test_llm_validation import SUBJECT, BODY, SENDER, good_payload


def row(payload=None, match_type="exact", status="NEXT_STEP_ASSESSMENT"):
    return {
        "id": "synthetic-1",
        "subject": SUBJECT,
        "body": BODY,
        "from_address": SENDER,
        "llm_output": payload if payload is not None else good_payload(),
        "gold_status": status,
        "gold_company": "Amazon",
        "gold_job_title": "Software Engineer",
        "match_type": match_type,
    }


def test_evaluator_counts_automatic_valid_case():
    out = evaluate([row()])
    assert out["emails"] == 1
    assert out["auto"] == 1
    assert out["auto_correct"] == 1
    assert out["auto_precision"] == 1


def test_evaluator_counts_wrong_label_in_automatic_cases():
    out = evaluate([row(status="REJECTED")])
    assert out["auto"] == 1
    assert out["false_auto"] == 1
    assert out["auto_precision"] == 0
    assert len(out["incorrect_auto_examples"]) == 1


def test_evaluator_counts_manual_review_for_fuzzy_match():
    out = evaluate([row(match_type="fuzzy")])
    assert out["auto"] == 0
    assert out["review"] == 1
    assert out["review_rate"] == 1
