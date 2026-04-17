"""Tests for the token bucket rate limiter."""

from app.core.rate_limiter import _TokenBucket


def test_bucket_allows_requests_up_to_capacity():
    bucket = _TokenBucket(capacity=5, refill_rate=5 / 60.0)
    results = [bucket.consume() for _ in range(5)]
    assert all(results)


def test_bucket_blocks_after_capacity():
    bucket = _TokenBucket(capacity=3, refill_rate=3 / 60.0)
    for _ in range(3):
        bucket.consume()
    assert not bucket.consume()


def test_bucket_refills_over_time():
    import time

    bucket = _TokenBucket(capacity=2, refill_rate=100.0)
    bucket.consume()
    bucket.consume()
    assert not bucket.consume()
    time.sleep(0.05)
    assert bucket.consume()
