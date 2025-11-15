from pathlib import Path
from urllib.parse import urlparse
from pydantic import BaseModel
from dataclasses import dataclass, fields
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]

class ProxySettings(BaseModel):
    server: str | None = None
    username: str | None = None
    password: str | None = None

    @property
    def url(self) -> str | None:
        """
        Full proxy URL with credentials if available, otherwise bare server.

        For aiohttp:
            proxy=self.url

        For Playwright:
            proxy={"server": server, "username": ..., "password": ...}
        """
        if self.server and self.username and self.password:
            parsed = urlparse(self.server)
            hostport = parsed.netloc or f"{parsed.hostname}:{parsed.port}"
            return f"{parsed.scheme}://{self.username}:{self.password}@{hostport}"
        return self.server

def load_proxy_from_txt(path: str) -> ProxySettings:
    """
    Load proxy settings from a text file containing a single URL line.

    The file itself (e.g. data/ProxyURL.txt) is git-ignored.
    A template like data/ProxyURL.example.txt can be committed instead.
    """
    
    p = Path(path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p

    if not p.exists():
        print("Proxy file not found:", p)
        return ProxySettings()

    raw = p.read_text(encoding="utf-8").strip()
    if not raw:
        print("Proxy file is empty:", p)
        return ProxySettings()

    lines = [ln.strip().strip('"').strip("'") for ln in raw.splitlines() if ln.strip()]
    line = lines[0]

    parsed = urlparse(line)
    if not parsed.scheme or not parsed.hostname:
        print("Proxy line does not look like a URL:", line)
        return ProxySettings()

    server = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port:
        server += f":{parsed.port}"

    return ProxySettings(
        server=server,
        username=parsed.username,
        password=parsed.password,
    )


@dataclass
class ScrapeConfig:
    """
    Central configuration for scraping behavior.

    Values can be overridden via scrape_config.yaml at the project root.
    """
    
    # General
    use_proxy: bool = True
    user_agent: str = "Mozilla/5.0"
    captcha_detection_bytes: int = 4096

    # HTTP client tuning
    http_concurrency: int = 20
    http_total_timeout_s: float = 20.0
    http_connect_timeout_s: float = 10.0
    http_sock_read_timeout_s: float = 15.0
    
    # HTTP retries
    http_max_retries: int = 1 
    http_retry_base_delay_s: float = 0.1
    http_retry_jitter_s: float = 0.2

    # Browser tuning
    browser_timeout_ms: int = 20_000
    browser_headless: bool = True
    browser_block_heavy: bool = True
    max_browser_escalations: int = 100  # cap escalated URLs per run
    browser_locale: str = "en-US"

    # Robotos cache
    robots_cache_path: str = "data/robots_cache.json"
    robots_cache_ttl_s: int = 24 * 3600

    # Escalation tuning
    escalation_min_bytes: int = 2048
    escalation_consider_latency: bool = False
    escalation_latency_s: float = 5.0

def load_scrape_config(path: str | Path | None = None) -> ScrapeConfig:
    """
    Load ScrapeConfig from YAML if present; otherwise use defaults.

    By default, looks for `scrape_config.yaml` at the project root.
    """

    if path is None:
        # src/settings.py → parent → project root
        base = PROJECT_ROOT
        path = base / "scrape_config.yaml"

    path = Path(path)

    if not path.exists():
        print(f"[config] YAML not found at {path}, using defaults")
        return ScrapeConfig()  # fallback
    
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}

    if not isinstance(data, dict):
        print(f"[config] Expected mapping in {path}, got {type(data)}, using defaults")
        return ScrapeConfig()

    allowed_keys = {f.name for f in fields(ScrapeConfig)}
    filtered = {k: v for k, v in data.items() if k in allowed_keys}

    return ScrapeConfig(**filtered)

DEFAULT_SCRAPE_CONFIG = load_scrape_config()
