"""
Policy module: decides whether an HTTP fetch should escalate to a heavier
browser-based scraper.

The logic is:
- explicit
- configurable
- easily auditable
"""

from src.metrics import FetchResult
from src.settings import ScrapeConfig


def should_escalate(r: FetchResult, config: ScrapeConfig | None = None) -> bool:
    # We only import here to avoid circular dependency
    from src.settings import DEFAULT_SCRAPE_CONFIG
    cfg = config or DEFAULT_SCRAPE_CONFIG
    
    if r.error_type == "robots_blocked":
        return False

    if r.captcha:
        return False

    if r.error_type is not None:
        return True

    if r.status is not None and r.status >= 400:
        return True

    # Tiny pages (might be partial, JS-reliant, or error stubs)
    if r.bytes_len < cfg.escalation_min_bytes:
        return True

    # Optionally (if enabled) treat very slow HTTP responses as candidates for browser escalation
    if cfg.escalation_consider_latency and r.ttl_s > cfg.escalation_latency_s:
        return True
    
    return False
