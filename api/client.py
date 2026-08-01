# api/client.py - HTTP client (stdlib urllib) with retry, errors, rate-limit tracking, caching.

import json
import logging
import time
import urllib.request
from urllib.error import HTTPError, URLError

from api.cache import Cache
import config as config_module

log = logging.getLogger("github-tui.client")

USER_AGENT = "github-tui/2.0.0"
TIMEOUT = 10
RETRY_BACKOFF = [1, 3, 7]
MAX_RETRIES = 3

TTL = {
    "search_results": 300,
    "repo_detail": 600,
    "readme": 3600,
    "trending": 1800,
    "user_profile": 600,
    "commits": 300,
    "issues": 300,
    "releases": 300,
    "contributors": 600,
    "languages": 600,
    "tree": 600,
    "rate_limit": 60,
}


class GitHubError(Exception):
    category = "generic"

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class NetworkError(GitHubError):
    category = "network_error"


class RateLimitError(GitHubError):
    category = "api_rate_limit"

    def __init__(self, message, reset_ts=None):
        super().__init__(message)
        self.reset_ts = reset_ts


class NotFoundError(GitHubError):
    category = "api_not_found"


class AuthError(GitHubError):
    category = "auth_error"


class ServerError(GitHubError):
    category = "api_server_error"


class ParseError(GitHubError):
    category = "parse_error"


class RateLimitState:
    """Track x-ratelimit-* headers; degrades gracefully when absent."""

    def __init__(self, default_limit=60):
        self.remaining = None
        self.limit = default_limit
        self.reset_ts = 0
        self.seen = False

    def update(self, headers):
        def _h(name):
            v = headers.get(name)
            if v is None and hasattr(headers, "get_all"):
                vals = headers.get_all(name)
                v = vals[0] if vals else None
            return v

        rem = _h("X-RateLimit-Remaining")
        lim = _h("X-RateLimit-Limit")
        res = _h("X-RateLimit-Reset")
        if rem is not None:
            self.remaining = int(rem)
            self.seen = True
        if lim is not None:
            self.limit = int(lim)
        if res is not None:
            self.reset_ts = int(res)

    def seconds_to_reset(self):
        if not self.reset_ts:
            return 0
        return max(0, int(self.reset_ts - time.time()))

    def label(self):
        if not self.seen:
            return "API --/--"
        return "API %d/%d" % (self.remaining or 0, self.limit)

    def low(self, threshold=10):
        return self.seen and self.remaining is not None and self.remaining <= threshold


class GitHubClient:
    def __init__(self, cfg=None, cache=None):
        self.cfg = cfg or config_module.Config.load()
        self.cache = cache or Cache(
            _cache_dir(), enabled=self.cfg.cache_enabled)
        self.rate = RateLimitState(5000 if self.cfg.token else 60)

    def _headers(self, extra=None):
        h = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": USER_AGENT,
        }
        if self.cfg.token:
            h["Authorization"] = "token %s" % self.cfg.token
        if extra:
            h.update(extra)
        return h

    def get(self, url, ttl=None, force=False, extra_headers=None, raw=False):
        """GET url with caching + retries. Returns parsed JSON (or raw text when raw=True).

        Raises GitHubError subclasses.
        """
        if ttl is None:
            ttl = self._guess_ttl(url)
        key = url + ("" if not self.cfg.token else "#" + self.cfg.token[:8])
        if not force:
            cached = self.cache.get(key, ttl)
            if cached is not None:
                return cached
        data = self._request(url, extra_headers=extra_headers, raw=raw)
        self.cache.set(key, data, ttl)
        return data

    def _request(self, url, extra_headers=None, raw=False, _depth=0):
        log.debug("GET %s", url)
        req = urllib.request.Request(url, headers=self._headers(extra_headers))
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                self.rate.update(resp.headers)
                body = resp.read()
                if raw:
                    return body.decode("utf-8", errors="replace")
                try:
                    return json.loads(body.decode("utf-8"))
                except ValueError:
                    log.exception("Parse error for %s", url)
                    raise ParseError("Malformed JSON from API")
        except HTTPError as e:
            self.rate.update(e.headers)
            return self._handle_http_error(e, url, _depth, extra_headers, raw)
        except URLError as e:
            log.warning("Network error for %s: %s", url, e.reason)
            raise NetworkError("Offline / connection failed: %s" % e.reason)
        except (TimeoutError, OSError) as e:
            log.warning("Network error for %s: %s", url, e)
            raise NetworkError("Connection failed: %s" % e)

    def _handle_http_error(self, e, url, depth, extra_headers=None, raw=False):
        code = e.code
        log.warning("HTTP %d for %s", code, url)
        if code == 429 or (code == 403 and not self.rate.remaining):
            reset = getattr(e.headers, "get", lambda k, d=None: d)("X-RateLimit-Reset")
            reset_ts = int(reset) if reset else self.rate.reset_ts
            raise RateLimitError("API rate limit reached", reset_ts=reset_ts)
        if code == 403:
            raise AuthError("Access forbidden (403) - check token / permissions")
        if code == 401:
            raise AuthError("Unauthorized (401) - invalid token")
        if code == 404:
            raise NotFoundError("Not found (404)")
        if code >= 500:
            if depth < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF[depth])
                return self._request(url, extra_headers=extra_headers, raw=raw, _depth=depth + 1)
            raise ServerError("Server error (HTTP %d)" % code)
        raise GitHubError("HTTP error %d" % code)

    def _guess_ttl(self, url):
        for kind, ttl in TTL.items():
            if kind in url:
                return ttl
        return 300

    def is_online(self):
        try:
            self.get("/rate_limit")
            return True
        except GitHubError:
            return False


def _cache_dir():
    import os
    return os.path.join(config_module.DATA_DIR, "cache")
