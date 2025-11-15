from src.metrics import FetchResult

def robots_blocked_result(url: str) -> FetchResult:
    """
    Convenience factory for a FetchResult representing a robots.txt denial.
    Used when RobotsCache.allowed(url) returns False so that the rest of the
    pipeline can treat it like any other FetchResult row.
    """
    return FetchResult(
        url=url,
        scraper="http",
        bytes_len=0,
        captcha=False,
        ttl_s=0.0,
        ttfb_s=None,
        error_type="robots_blocked",
        status=None
    )

# Error types for which it is reasonable to retry the HTTP request.
RETRYABLE_ERRORS = {
    "TimeoutError",
    "ClientConnectorError",
    "ClientHttpProxyError",
    "ClientPayloadError",
}
