from src.policy import should_escalate
from src.metrics import FetchResult
from src.settings import ScrapeConfig


def make_result(**overrides) -> FetchResult:
    """Helper: start from a 'clean success' and override fields."""
    base = FetchResult(
        url="https://example.com",
        scraper="http",
        bytes_len=10_000,
        captcha=False,
        ttl_s=1.0,
        ttfb_s=0.1,
        error_type=None,
        status=200,
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


def test_clean_success_does_not_escalate():
    r = make_result()
    assert not should_escalate(r)


def test_robots_blocked_never_escalate():
    r = make_result(error_type="robots_blocked")
    assert not should_escalate(r)


def test_captcha_does_not_escalate():
    r = make_result(captcha=True)
    assert not should_escalate(r)


def test_http_error_escalates():
    r = make_result(status=404)
    assert should_escalate(r)


def test_transport_error_escalates():
    r = make_result(error_type="TimeoutError", status=None)
    assert should_escalate(r)


def test_tiny_body_escalates():
    cfg = ScrapeConfig(escalation_min_bytes=5000)
    r = make_result(bytes_len=1000)
    assert should_escalate(r, config=cfg)


def test_latency_based_escalation_when_enabled():
    cfg = ScrapeConfig(
        escalation_min_bytes=0,
        escalation_consider_latency=True,
        escalation_latency_s=1.0,
    )
    r = make_result(ttl_s=2.0, bytes_len=50_000)
    assert should_escalate(r, config=cfg)