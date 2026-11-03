"""UTC publication timestamps and exact rolling job-posting windows.

A job's first appearance in our database is not its employer's publication time.
Only source-provided publication timestamps qualify for a "posted within" filter.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

POSTED_WITHIN_HOURS = {'4h': 4, '24h': 24, '7d': 168, '30d': 720}


def utc_naive(value: datetime) -> datetime:
    """Normalize timezone-aware dates to UTC and use naive UTC in DB DateTime."""
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def parse_published_at(value) -> Optional[datetime]:
    """Parse source-provided ISO dates or Lever's epoch milliseconds.

    Unknown publication time remains None. Never invent it from scrape time.
    """
    if value is None or value == '':
        return None
    try:
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, (int, float)) or (isinstance(value, str) and value.strip().isdigit()):
            stamp = float(value)
            if stamp > 1e11:
                stamp /= 1000
            parsed = datetime.fromtimestamp(stamp, tz=timezone.utc)
        elif isinstance(value, str):
            parsed = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
        else:
            return None
        return utc_naive(parsed)
    except (ValueError, OverflowError, TypeError, OSError):
        return None


def apply_published_window(query, job_model, posted_within: Optional[str], now: Optional[datetime] = None):
    """Filter by actual publication timestamp within a UTC rolling window."""
    if not posted_within or posted_within == 'all':
        return query
    hours = POSTED_WITHIN_HOURS.get(posted_within)
    if hours is None:
        raise ValueError(f'Unsupported published-window filter: {posted_within}')
    current = utc_naive(now or datetime.now(timezone.utc))
    return query.filter(
        job_model.posted_at.isnot(None),
        job_model.posted_at >= current - timedelta(hours=hours),
        job_model.posted_at <= current,
    )
