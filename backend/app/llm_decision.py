"""Independent safety gates for LLM-assisted recruitment email classification.

This score measures satisfied verification checks, NOT a calibrated probability.
Use a held-out labeled email set to choose policy thresholds for real traffic.
"""
import re
from typing import Dict, Tuple

# Explicit *actionable* wording in the evidence quote. Avoid generic words such
# as "unfortunately", "offer", "calendar" or "available" by themselves.
PATTERNS = {
    "applied": [
        r"\bthank you for (?:your application|applying)\b",
        r"\b(?:application (?:has been |was )?(?:received|submitted|confirmed))\b",
        r"\bsuccessfully (?:submitted|applied)\b",
    ],
    "assessment": [
        r"\b(?:complete|take|start|begin|finish|submit)\b.{0,45}\b(?:assessment|coding challenge|technical evaluation|programming test|take.home)\b",
        r"\b(?:invited|invite|invitation)\b.{0,55}\b(?:coding|technical|programming)\b.{0,20}\b(?:assessment|challenge|evaluation|test)\b",
        r"\b(?:coding|technical|programming)\b.{0,24}\b(?:assessment|challenge|evaluation|exercise|test)\b.{0,30}\b(?:due|deadline|by (?:friday|monday|tuesday|wednesday|thursday|saturday|sunday))\b",
    ],
    "interview_scheduled": [
        r"\binterview\b.{0,45}\b(?:is scheduled|has been scheduled|confirmed|booked)\b",
        r"\b(?:confirmed|scheduled|booked)\b.{0,45}\binterview\b",
    ],
    "rejected": [
        r"\b(?:not moving forward|not selected|regret to inform|will not be proceeding)\b",
        r"\b(?:pursue|moving forward with|selected)\b.{0,28}\bother candidates\b",
        r"\b(?:application|candidacy)\b.{0,45}\bunsuccessful\b",
    ],
    "offer": [
        r"\b(?:pleased|delighted|excited) to offer you\b.{0,50}\b(?:position|role|job|employment)\b",
        r"\b(?:extend|extended|extending) (?:you )?an? (?:employment |job )?offer\b",
        r"\b(?:formal )?offer (?:of employment|letter)\b",
    ],
}

# Explicit negatives such as "the assessment is not required" should never
# be interpreted as a positive invitation to complete an assessment.
NEGATIVE_ACTION = re.compile(
    r"\b(?:no|not|never|without|cancelled|canceled)\b.{0,35}"
    r"\b(?:assessment|interview|coding challenge|test|offer)\b"
    r"|\b(?:assessment|interview|offer)\b.{0,20}\b(?:not required|cancelled|canceled|withdrawn)\b",
    re.IGNORECASE,
)


def status_signals(source: str) -> set:
    text = " ".join((source or "").casefold().split())
    if NEGATIVE_ACTION.search(text):
        # This is deliberately conservative; request review on negated context.
        return set()
    return {
        name for name, patterns in PATTERNS.items()
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)
    }


def verify_llm_status(
    predicted: str, evidence_quote: str, full_text: str,
    rule_status: str
) -> Tuple[int, bool, str]:
    """Score independent checks, then decide if this prediction may be automated.

    Scores are deterministic quality-policy points, *not* accuracy percentages.
    Auto eligibility is a conjunction of evidence support, non-conflict, and
    policy gates; an application match is checked separately by matcher.py.
    """
    status = "applied" if predicted == "received" else predicted
    signal = status_signals(evidence_quote)
    full_signals = status_signals(full_text)
    matches_evidence = status in signal

    # An application receipt commonly accompanies a next-step invitation.
    other = full_signals - {status, "applied"}
    contradiction = bool(other)
    if status == "applied" and (full_signals - {"applied"}):
        contradiction = True
    if not matches_evidence:
        return 50, False, "status not independently supported by evidence"
    if contradiction:
        return 80, False, "multiple conflicting application stages in email"

    rule_agrees = status == rule_status
    score = 50 + 30 + 15 + (5 if rule_agrees else 0)

    # Final outcomes require agreement from two independent sources.
    if status in {"rejected", "offer"} and not rule_agrees:
        return score, False, "high-impact status needs independent agreement"

    # Every status needs source evidence; the application match must also be
    # exact (or a verified new application confirmation) before an update.
    return score, score >= 95, "source-backed status, no contradictions"
