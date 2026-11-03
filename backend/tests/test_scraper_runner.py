"""Verify independent provider scrapers overlap and URL dedup stays centralized."""
from pathlib import Path
from threading import Barrier
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scrapers import runner


def test_provider_loops_are_concurrent_and_urls_are_unique(monkeypatch):
    # Sequential calls would time out waiting for the other two providers.
    barrier = Barrier(3, timeout=3)

    def scraper(name, url):
        def run():
            barrier.wait()
            return [{'source_url': url, 'company': name}]
        return run

    monkeypatch.setattr(runner.greenhouse, 'scrape', scraper('gh', 'https://example.org/a'))
    monkeypatch.setattr(runner.lever, 'scrape', scraper('lever', 'https://example.org/a'))
    monkeypatch.setattr(runner.ashby, 'scrape', scraper('ashby', 'https://example.org/b'))
    result = runner.run_all(run_linkedin=False)
    assert {job['source_url'] for job in result} == {'https://example.org/a', 'https://example.org/b'}
    assert len(result) == 2


def test_one_provider_failing_does_not_block_another(monkeypatch):
    def broken():
        raise RuntimeError('provider outage')
    monkeypatch.setattr(runner.greenhouse, 'scrape', broken)
    monkeypatch.setattr(runner.lever, 'scrape', lambda: [{'source_url': 'https://example.org/ok'}])
    result = runner.run_all(run_linkedin=False, run_ashby=False)
    assert [p['source_url'] for p in result] == ['https://example.org/ok']
