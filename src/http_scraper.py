import time, aiohttp
from .metrics import FetchResult
from .settings import ScrapeConfig, ProxySettings


DEFAULT_HTTP_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

class HttpScraper:
    """
    Lightweight HTTP fetcher built on aiohttp.

    - Supports proxy usage
    - Controlled by ScrapeConfig (timeouts, UA, retries are handled outside)
    - Measures TTL, TTFB
    - Detects CAPTCHA heuristically using the first bytes of HTML
    """
    name = "http"

    def __init__(self, session: aiohttp.ClientSession, config: ScrapeConfig, proxy: ProxySettings | None = None):
        self.session = session
        self.config = config
        self.proxy = proxy

    async def fetch(self, url: str) -> FetchResult:
        """
        Fetch a URL using aiohttp.

        Returns:
            FetchResult with timing, status code,
            CAPTCHA flag, and error type if failed.
        """
        t0 = time.perf_counter()
        ttfb = None

        proxy_url = self.proxy.url if (self.proxy and self.config.use_proxy) else None
        headers = {**DEFAULT_HTTP_HEADERS, "User-Agent": self.config.user_agent}

        try:
            async with self.session.get(
                url, proxy=proxy_url, headers = headers,
                timeout=self.config.http_total_timeout_s, allow_redirects = True
            ) as resp:
                ttfb = time.perf_counter() - t0
                body = await resp.read()
                ttl = time.perf_counter() - t0

                lower = body[: self.config.captcha_detection_bytes].lower()
                is_captcha = (b"captcha" in lower) or (b"are you a robot" in lower)

                return FetchResult(url=url, scraper=self.name, bytes_len=len(body), captcha=is_captcha, ttl_s=ttl, ttfb_s=ttfb, error_type=None, status=resp.status, retry_count=0)
        except Exception as e:
            ttl = time.perf_counter() - t0
            return FetchResult(url=url, scraper=self.name, bytes_len=0, captcha=False, ttl_s=ttl, ttfb_s=ttfb, error_type=type(e).__name__, status=None, retry_count=0)
