"""Unified HTTP client with UA rotation, rate limiting, and exponential backoff."""

import random
import time
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]

# Per-domain minimum intervals (seconds)
RATE_LIMITS = {
    "export.arxiv.org": 3.0,
    "api.semanticscholar.org": 1.0,  # with key; 3.0 without
    "huggingface.co": 2.0,
}

_last_request_time: dict[str, float] = {}


def _get_domain(url: str) -> str:
    from urllib.parse import urlparse
    return urlparse(url).netloc


def _get_proxies() -> dict | None:
    """Read proxy config from env. Returns None if not set."""
    http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
    if not http_proxy and not https_proxy:
        return None
    proxies = {}
    if http_proxy:
        proxies["http"] = http_proxy
    if https_proxy:
        proxies["https"] = https_proxy
    return proxies


def _get_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    proxies = _get_proxies()
    if proxies:
        session.proxies.update(proxies)
        print(f"[http] Proxy enabled: {proxies}")
    return session

_session = _get_session()


def _wait_for_rate_limit(domain: str):
    """Enforce per-domain rate limiting."""
    s2_key = os.getenv("S2_API_KEY")
    min_interval = RATE_LIMITS.get(domain, 1.0)
    if domain == "api.semanticscholar.org" and not s2_key:
        min_interval = 3.0
    last = _last_request_time.get(domain, 0)
    elapsed = time.time() - last
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    _last_request_time[domain] = time.time()


def fetch(url: str, params: dict | None = None, headers: dict | None = None,
          max_retries: int = 5, initial_backoff: float = 5.0) -> requests.Response:
    """Fetch URL with UA rotation, rate limiting, and exponential backoff for 429s."""
    domain = _get_domain(url)
    hdrs = {"User-Agent": random.choice(USER_AGENTS)}

    # Add S2 API key if available
    if domain == "api.semanticscholar.org":
        s2_key = os.getenv("S2_API_KEY")
        if s2_key:
            hdrs["x-api-key"] = s2_key

    if headers:
        hdrs.update(headers)

    backoff = initial_backoff
    for attempt in range(max_retries):
        _wait_for_rate_limit(domain)
        resp = _session.get(url, params=params, headers=hdrs, timeout=30)
        if resp.status_code == 429:
            wait = min(backoff * (2 ** attempt), 300)
            print(f"[http] 429 from {domain}, backing off {wait:.0f}s (attempt {attempt+1}/{max_retries})")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp

    raise RuntimeError(f"Max retries exceeded for {url}")
