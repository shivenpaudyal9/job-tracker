"""Regression tests for publication time vs. first-seen scrape time."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import Column, DateTime, Integer, create_engine
from sqlalchemy.orm import declarative_base, Session
from app.job_freshness import apply_published_window, parse_published_at

Base = declarative_base()


class Listing(Base):
    __tablename__ = 'freshness_test_listings'
    id = Column(Integer, primary_key=True)
    posted_at = Column(DateTime)
    scraped_at = Column(DateTime)


def test_source_utc_normalization_and_lever_milliseconds():
    assert parse_published_at('2026-11-03T16:00:00Z') == datetime(2026, 11, 3, 16)
    assert parse_published_at('2026-11-03T10:00:00-06:00') == datetime(2026, 11, 3, 16)
    assert parse_published_at(1793721600000) == datetime(2026, 11, 3, 16)
    assert parse_published_at('not a date') is None
    assert parse_published_at(None) is None


def test_rolling_windows_use_published_not_scraped_time():
    now = datetime(2026, 11, 3, 16)
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([
            Listing(id=1, posted_at=now-timedelta(days=8), scraped_at=now-timedelta(minutes=3)),
            Listing(id=2, posted_at=now-timedelta(hours=3), scraped_at=now-timedelta(minutes=10)),
            Listing(id=3, posted_at=now-timedelta(hours=23), scraped_at=now),
            Listing(id=4, posted_at=None, scraped_at=now),
            Listing(id=5, posted_at=now+timedelta(days=1), scraped_at=now),
        ])
        session.commit()
        base = session.query(Listing)
        assert [x.id for x in apply_published_window(base, Listing, '4h', now).order_by(Listing.id)] == [2]
        assert [x.id for x in apply_published_window(base, Listing, '24h', now).order_by(Listing.id)] == [2, 3]
        assert [x.id for x in apply_published_window(base, Listing, '7d', now).order_by(Listing.id)] == [2, 3]
        assert [x.id for x in apply_published_window(base, Listing, '30d', now).order_by(Listing.id)] == [1, 2, 3]
        assert [x.id for x in apply_published_window(base, Listing, 'all', now).order_by(Listing.id)] == [1, 2, 3, 4, 5]


def test_unknown_and_invalid_dates():
    assert parse_published_at('') is None
    assert parse_published_at(float('inf')) is None
    assert parse_published_at(datetime(2026, 11, 3, 10, tzinfo=timezone(timedelta(hours=-6)))) == datetime(2026, 11, 3, 16)
    try:
        apply_published_window(None, Listing, 'bad')
    except ValueError:
        pass
    else:
        raise AssertionError('Invalid filters must fail')
