import time
from playwright.async_api import async_playwright
from .metrics import FetchResult
from .settings import ProxySettings, ScrapeConfig

class BrowserScraper:
    """
    Heavyweight JS-enabled fetcher using Playwright.

    - Uses single browser instance per context manager (__aenter__/__aexit__)
    - Supports proxy authentication
    - Configurable headers, locale, headless mode, and heavy-resource blocking
    - Measures TTL, TTFB
    - Detects simple CAPTCHAs in rendered DOM
    """

    name = "browser"

    def __init__(self, config: ScrapeConfig ,proxy: ProxySettings | None = None):
        self.config = config
        self.proxy = proxy
        
        self._playwright = None
        self._browser = None
        self._context = None
    
    async def __aenter__(self):
        self._playwright = await async_playwright().start()

        # Build proxy config dict if enabled
        proxy_dict = None
        if self.proxy and self.proxy.server and self.config.use_proxy:
            proxy_dict = {"server": self.proxy.server}
            if self.proxy.username and self.proxy.password:
                proxy_dict["username"] = self.proxy.username
                proxy_dict["password"] = self.proxy.password

        # Launch browser
        self._browser = await self._playwright.chromium.launch(
            headless=self.config.browser_headless,
            proxy=proxy_dict,
        )

        # Create context
        self._context = await self._browser.new_context(
            user_agent=self.config.user_agent,
            locale=self.config.browser_locale,
        )

        # Optional: block heavy resources
        if self.config.browser_block_heavy:
            async def route_handler(route):
                if route.request.resource_type in {"image", "media", "font"}:
                    await route.abort()
                else:
                    await route.continue_()
            await self._context.route("**/*", route_handler)

        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()


    async def fetch(self, url: str) -> FetchResult:
        t0 = time.perf_counter()
        ttfb = None
        page = await self._context.new_page()

        try:
            resp = await page.goto(url, timeout=self.config.browser_timeout_ms, wait_until="domcontentloaded")
            ttfb = time.perf_counter() - t0
            html = await page.content()
            ttl = time.perf_counter() - t0

            lower = html[: self.config.captcha_detection_bytes].lower()
            is_captcha = ("captcha" in lower) or ("are you a robot" in lower)
            status = resp.status if resp else 200
            return FetchResult(url=url, scraper=self.name, bytes_len=len(html.encode("utf-8","ignore")), captcha=is_captcha, ttl_s=ttl, ttfb_s=ttfb, error_type=None, status=status, retry_count=0)
        
        except Exception as e:
            ttl = time.perf_counter() - t0
            return FetchResult(url=url, scraper=self.name, bytes_len=0, captcha=False, ttl_s=ttl, ttfb_s=ttfb, error_type=type(e).__name__, status=None, retry_count=0)
        
        finally:
            await page.close()
