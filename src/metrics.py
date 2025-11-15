from dataclasses import dataclass

@dataclass
class FetchResult:
    """
    Normalized per-URL result used by both HTTP and browser scrapers.

    Fields:
        url         : The URL that was requested.
        scraper     : Name of the scraper, e.g. "http" or "browser".
        bytes_len   : Length of the fetched content in bytes (0 on failure).
        captcha     : Heuristic flag for CAPTCHA / "are you a robot" pages.
        ttl_s       : Total time to last byte (seconds).
        ttfb_s      : Time to first byte (seconds), if measurable.
        error_type  : String name of the error/exception (e.g. "TimeoutError"),
                      or "robots_blocked" when filtered before request.
        status      : HTTP status code if available (e.g. 200, 404).
        domain      : Normalized registrable domain (filled in later).
        proxy_hint  : "proxy" vs "direct" - how this request was routed.
        retry_count : Number of retries attempted for this URL (HTTP only).
    """
    url: str
    scraper: str
    bytes_len: int
    captcha: bool
    ttl_s: float
    ttfb_s: float | None
    error_type: str | None
    status: int | None = None
    domain: str | None = None
    proxy_hint: str | None = None
    retry_count: int = 0
