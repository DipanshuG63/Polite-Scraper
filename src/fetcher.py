"""Small sequential HTTP client, with cache and per-request politeness."""
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import time
from urllib.parse import urlparse

import requests

ALLOWED_HOST = "books.toscrape.com"


@dataclass
class FetchStats:
    pages_fetched: int = 0
    cache_hits: int = 0


class PoliteFetcher:
    def __init__(self, cache_dir: Path, user_agent: str, timeout: float = 10.0, delay: float = 0.5):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.delay = max(float(delay), 0.5)  # Never send real requests faster than assignment allows.
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent, "Accept-Language": "en-US,en;q=0.9"})
        self.last_real_request: float | None = None
        self.stats = FetchStats()
        self.fetched_at: dict[str, str] = {}

    @staticmethod
    def _check_url(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST or parsed.port is not None:
            raise ValueError(f"Disallowed target URL: {url}")
        if parsed.username or parsed.password:
            raise ValueError(f"Disallowed URL credentials: {url}")

    def _cache_path(self, url: str, cache_key: str | None = None) -> Path:
        # Hash the URL to avoid path-traversal and accidental filename collisions.
        if cache_key:
            if not cache_key.isidentifier() and not all(c.isalnum() or c in "-_" for c in cache_key):
                raise ValueError("Invalid cache key")
            filename = cache_key + ".html"
        else:
            filename = "book-" + sha256(url.encode("utf-8")).hexdigest() + ".html"
        return self.cache_dir / filename

    def _polite_wait(self) -> None:
        if self.last_real_request is None:
            return
        elapsed = time.monotonic() - self.last_real_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

    def get(self, url: str, cache_key: str | None = None, use_cache: bool = True) -> tuple[str, str]:
        self._check_url(url)  # Validate even on cache hits.
        path = self._cache_path(url, cache_key)
        if use_cache and path.is_file():
            self.stats.cache_hits += 1
            self.fetched_at[url] = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
            return path.read_text(encoding="utf-8"), "CACHE HIT"

        for attempt in range(2):
            self._polite_wait()
            self.last_real_request = time.monotonic()  # Update for ALL real requests, including failed ones.
            try:
                response = self.session.get(url, timeout=self.timeout, allow_redirects=False)
            except (requests.Timeout, requests.ConnectionError) as exc:
                if attempt == 0:
                    time.sleep(1.0)
                    continue
                raise RuntimeError(f"request failed after retry: {exc}") from exc

            if response.status_code == 200:
                # Books to Scrape's body is UTF-8. requests often defaults to Latin-1,
                # producing 'Â£' and broken apostrophes if response.text is used blindly.
                try:
                    html = response.content.decode("utf-8")
                except UnicodeError as exc:
                    raise RuntimeError("Response is not valid UTF-8 HTML") from exc
                path.write_text(html, encoding="utf-8")
                self.fetched_at[url] = datetime.now(timezone.utc).isoformat()
                self.stats.pages_fetched += 1
                return html, "FETCH"
            if response.status_code in (403, 404, 429):
                # A 403/429 is a stop signal, not a reason to keep trying.
                raise RuntimeError(f"HTTP {response.status_code}")
            if 500 <= response.status_code <= 599 and attempt == 0:
                time.sleep(1.0)
                continue
            raise RuntimeError(f"HTTP {response.status_code}")
        raise RuntimeError("request failed after retry")
