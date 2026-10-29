"""Validation helpers for untrusted LLM email-extraction responses.

This checks that suggested fields have verbatim supporting text in the email.
The quality score is a *routing heuristic*, never a calibrated probability.
"""
from typing import Any, Dict, Optional


VALID_STATUSES = {
    "applied", "received", "interview_scheduled",
    "assessment", "rejected", "offer",
}


def _clean(value: Any, max_len: int = 200) -> Optional[str]:
    if not isinstance(value, str):
        return None
    value = " ".join(value.strip().split())
    return value if 0 < len(value) <= max_len else None


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def _supported(quote: Any, source: str, field: Optional[str] = None) -> bool:
    quote = _clean(quote, max_len=350)
    if not quote or len(quote) < 8:
        return False
    if _normalize(quote) not in _normalize(source):
        return False
    return field is None or _normalize(field) in _normalize(quote)


def validate_llm_payload(
    data: Any, subject: str, body: str, from_address: str
) -> Optional[Dict[str, Any]]:
    """Return grounded fields or None; never trust JSON shape or LLM claims alone."""
    if not isinstance(data, dict) or data.get("is_job_related") is not True:
        return None
    status = data.get("status")
    if not isinstance(status, str) or status not in VALID_STATUSES:
        return None

    source = "\n".join([subject or "", body or "", from_address or ""])
    company = _clean(data.get("company_name"))
    title = _clean(data.get("job_title"))
    if not company or not title:
        return None
    if not _supported(data.get("status_evidence"), source):
        return None
    if not _supported(data.get("company_evidence"), source, company):
        return None
    if not _supported(data.get("job_title_evidence"), source, title):
        return None

    action_required = data.get("action_required")
    if type(action_required) is not bool:
        return None
    action_description = _clean(data.get("action_description"), max_len=500)
    action_quote = data.get("action_evidence")
    if action_required and (not action_description or not _supported(action_quote, source)):
        return None

    return {
        "company_name": company,
        "job_title": title,
        "status": status,
        "action_required": action_required,
        "action_description": action_description if action_required else None,
    }
