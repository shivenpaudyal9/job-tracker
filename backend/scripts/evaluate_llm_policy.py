"""Offline safety/automation evaluation on HUMAN-LABELED recruiter emails.

Usage: cd backend && python scripts/evaluate_llm_policy.py /path/to/labeled.jsonl

Input JSONL rows:
{
  "id": "redacted-001",
  "subject": "Your ... application",
  "body": "...",
  "from_address": "recruiting@example.com",
  "llm_output": { ... exact JSON schema returned by Llama ... },
  "gold_status": "NEXT_STEP_ASSESSMENT",
  "gold_company": "Example",
  "gold_job_title": "Software Engineer",
  "match_type": "exact"
}

match_type is the independently verified application-match outcome
(exact, fuzzy, no_match). The evaluator replays the LLM response through
the SAME extractor; it never contacts Groq or sends personal emails anywhere.

This evaluates routing behavior, not calibrated probabilities.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.extractor import JobEmailExtractor
from app.models import ApplicationStatus


class ReplayLLM:
    def __init__(self, payload):
        self.payload = payload
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.complete))

    def complete(self, **_kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(self.payload)))]
        )


def evaluate(rows):
    totals = {
        "emails": 0, "auto": 0, "auto_correct": 0,
        "review": 0, "false_auto": 0,
    }
    outcomes = defaultdict(lambda: {"auto": 0, "correct": 0})
    errors = []
    for row in rows:
        totals["emails"] += 1
        pred = JobEmailExtractor(llm_client=ReplayLLM(row["llm_output"])).extract(
            row["subject"], row["body"], row.get("from_address", ""),
        )
        verified = (
            pred.extraction_method.startswith("llm_")
            and pred.verification_score is not None
            and pred.verification_score >= 95
            and not pred.requires_manual_review
        )
        match = row["match_type"]
        safe_match = (match == "exact") or (
            match == "no_match" and pred.status == ApplicationStatus.APPLIED_RECEIVED
        )
        auto = verified and safe_match
        correct = (
            pred.status.value == row["gold_status"]
            and (pred.company_name or "").strip().casefold() == row["gold_company"].strip().casefold()
            and (pred.job_title or "").strip().casefold() == row["gold_job_title"].strip().casefold()
        )
        if auto:
            totals["auto"] += 1
            outcomes[pred.status.value]["auto"] += 1
            if correct:
                totals["auto_correct"] += 1
                outcomes[pred.status.value]["correct"] += 1
            else:
                totals["false_auto"] += 1
                errors.append({
                    "id": row.get("id", "not supplied"),
                    "expected": row["gold_status"],
                    "predicted": pred.status.value,
                    "match_type": match,
                    "verification_score": pred.verification_score,
                })
        else:
            totals["review"] += 1

    n = totals["emails"]
    auto_count = totals["auto"]
    return {
        **totals,
        "auto_coverage": auto_count / n if n else None,
        "auto_precision": totals["auto_correct"] / auto_count if auto_count else None,
        "review_rate": totals["review"] / n if n else None,
        "by_predicted_status": dict(outcomes),
        "incorrect_auto_examples": errors,
        "important": "Only evaluated on provided labeled data. No score is a calibrated probability.",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("labeled_jsonl", type=Path)
    args = ap.parse_args()
    with args.labeled_jsonl.open(encoding="utf-8") as f:
        rows = (json.loads(line) for line in f if line.strip())
        print(json.dumps(evaluate(rows), indent=2))


if __name__ == "__main__":
    main()
