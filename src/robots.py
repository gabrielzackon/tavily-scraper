import time
from urllib.parse import urlparse
import aiohttp
from .settings import ScrapeConfig, PROJECT_ROOT


class RobotsCache:
    """
    Simple persistent robots.txt cache with TTL.

    What this implementation does:
    - Caches a single boolean per origin (scheme://host)
    - Only answers the question: "Does robots.txt fully forbid this site?"

    Behavior:
    - If robots.txt is unreachable or malformed - allow (and cache)
    - Cache entries expire every `ttl_s` seconds
    - Cached on disk at `config.robots_cache_path`
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        config: ScrapeConfig,
    ):
        self.session = session
        self.user_agent = config.user_agent
        self.cache_path = (PROJECT_ROOT / config.robots_cache_path).resolve()
        self.ttl_s = config.robots_cache_ttl_s
        self._cache: dict[str, dict] = {}
        self._load_cache()


    async def allowed(self, url: str) -> bool:
        """
        Returns True if allowed to fetch this URL according to robots.txt.
        Uses:
            - cached decision (if fresh)
            - fallback if robots.txt cannot be fetched
        """

        origin = self._origin_from_url(url)

        cached = self._get_cached(origin)
        if cached is not None:
            return cached

        # Not in cache or expired - fetch robots.txt
        robots_url = f"{origin}/robots.txt"

        try:
            text = await self._fetch_robots(robots_url)
        except Exception:
            # If robots retrieval fails, be permissive but cache the decision
            self._store(origin, True)
            return True

        if text is None:
            # No robots.txt - allow
            self._store(origin, True)
            return True

        allowed = self._parse_robots(text, self.user_agent)
        self._store(origin, allowed)
        return allowed


    def _origin_from_url(self, url: str) -> str:
        """
        Normalize a URL to its origin: scheme://host
        """
        parsed = urlparse(url)
        scheme = parsed.scheme or "https"
        host = parsed.netloc
        return f"{scheme}://{host}"

    def _get_cached(self, origin: str) -> bool | None:
        """
        Returns None if not cached or expired, otherwise returns allowed/disallowed
        """
        entry = self._cache.get(origin)
        if not entry:
            return None
        ts = entry.get("ts")
        if ts is None or (time.time() - ts) > self.ttl_s:
            # Expired
            return None
        return bool(entry.get("allowed", True))

    def _store(self, origin: str, allowed: bool) -> None:
        """
        Store the robots decision in memory and persist to disk
        """
        self._cache[origin] = {"allowed": bool(allowed), "ts": time.time()}
        self._save_cache()

    async def _fetch_robots(self, robots_url: str) -> str | None:
        """
        Try to retrieve robots.txt with a short timeout
        Returns None if the file does not exist or cannot be parsed
        """
        try:
            async with self.session.get(robots_url, timeout=10) as resp:
                if resp.status >= 400:
                    return None
                return await resp.text()
        except Exception:
            return None

    def _parse_robots(self, content: str, user_agent: str) -> bool:
        """
        Extremely simplified robots.txt parser.

        Strategy:
        - Find the active User-agent block: exact match OR '*' fallback
        - If that block has 'Disallow: /' - deny
        - Everything else (including Disallow of partial paths) - allow
        """
        lines = [ln.strip() for ln in content.splitlines()]
        ua = user_agent.lower()
        active_block = None   # None / "us" / "star"

        allowed = True  # default allow

        for ln in lines:
            if not ln or ln.startswith("#"):
                continue

            lower = ln.lower()
            if lower.startswith("user-agent:"):
                value = lower.split(":", 1)[1].strip()
                if value == "*":
                    active_block = "star"
                elif value in ua:
                    active_block = "us"
                else:
                    active_block = None
                continue

            if lower.startswith("disallow:") and active_block in {"star", "us"}:
                rule = lower.split(":", 1)[1].strip()
                if rule == "/" or rule == "/*":
                    allowed = False

        return allowed


    def _load_cache(self) -> None:
        """
        Load robots decisions from disk.
        """
        if not self.cache_path.exists():
            return
        try:
            import json

            raw = self.cache_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                self._cache = data
        except Exception:
            self._cache = {}

    def _save_cache(self) -> None:
        """
        Persist robots decisions to disk.
        """
        try:
            import json

            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(
                json.dumps(self._cache, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            # Don't crash scraping due to cache save failure
            pass
