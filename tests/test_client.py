import json
import tempfile
import time
import unittest
from unittest import mock
from urllib.error import HTTPError, URLError

from api.client import (GitHubClient, NetworkError, RateLimitError,
                        NotFoundError, AuthError, ServerError, ParseError)
from api.cache import Cache
from config import Config


class FakeResponse:
    def __init__(self, data, headers=None, code=200):
        self._data = data if isinstance(data, bytes) else json.dumps(data).encode()
        self.headers = headers or {}
        self.code = code

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeHTTPError(HTTPError):
    def __init__(self, code, headers=None):
        HTTPError.__init__(self, "http://fake", code, "boom", headers or {}, None)


def _client(cache_dir=None):
    cfg = Config({"token": ""})
    cache = Cache(cache_dir or tempfile.mkdtemp(), enabled=True)
    return GitHubClient(cfg, cache)


class TestClient(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def test_success(self):
        c = _client(self.dir)
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse({"items": [1]})):
            data = c.get("http://x/search/repositories")
        self.assertEqual(data, {"items": [1]})

    def test_cache_hit_no_request(self):
        c = _client(self.dir)
        c.cache.set("http://x/search/repositories", {"cached": True})
        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("no request")):
            data = c.get("http://x/search/repositories")
        self.assertEqual(data, {"cached": True})

    def test_force_bypasses_cache(self):
        c = _client(self.dir)
        c.cache.set("http://x/search/repositories", {"cached": True})
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse({"fresh": True})):
            data = c.get("http://x/search/repositories", force=True)
        self.assertEqual(data, {"fresh": True})

    def test_404(self):
        c = _client(self.dir)
        with mock.patch("urllib.request.urlopen",
                        side_effect=FakeHTTPError(404)):
            with self.assertRaises(NotFoundError):
                c.get("http://x/repos/a/b", force=True)

    def test_401_auth(self):
        c = _client(self.dir)
        with mock.patch("urllib.request.urlopen", side_effect=FakeHTTPError(401)):
            with self.assertRaises(AuthError):
                c.get("http://x/user", force=True)

    def test_429_rate_limit(self):
        c = _client(self.dir)
        headers = {"X-RateLimit-Reset": str(int(time.time()) + 120)}
        with mock.patch("urllib.request.urlopen",
                        side_effect=FakeHTTPError(429, headers)):
            with self.assertRaises(RateLimitError) as cm:
                c.get("http://x/search/repositories", force=True)
            self.assertIsNotNone(cm.exception.reset_ts)

    def test_403_no_remaining_is_rate_limit(self):
        c = _client(self.dir)
        c.rate.remaining = 0
        with mock.patch("urllib.request.urlopen",
                        side_effect=FakeHTTPError(403, {"X-RateLimit-Reset": "0"})):
            with self.assertRaises(RateLimitError):
                c.get("http://x/search/repositories", force=True)

    def test_5xx_retries_then_succeeds(self):
        c = _client(self.dir)
        ok = FakeResponse({"ok": 1})
        with mock.patch("urllib.request.urlopen", side_effect=[FakeHTTPError(500), ok]) as m:
            data = c.get("http://x/search/repositories", force=True)
        self.assertEqual(data, {"ok": 1})
        self.assertEqual(m.call_count, 2)

    def test_5xx_exhausts_retries(self):
        c = _client(self.dir)
        with mock.patch("api.client.time.sleep"), \
             mock.patch("urllib.request.urlopen",
                        side_effect=FakeHTTPError(503)):
            with self.assertRaises(ServerError):
                c.get("http://x/search/repositories", force=True)

    def test_network_error(self):
        c = _client(self.dir)
        with mock.patch("urllib.request.urlopen", side_effect=URLError("down")):
            with self.assertRaises(NetworkError):
                c.get("http://x/search/repositories", force=True)

    def test_parse_error(self):
        c = _client(self.dir)
        resp = FakeResponse(b"{not json")
        with mock.patch("urllib.request.urlopen", return_value=resp):
            with self.assertRaises(ParseError):
                c.get("http://x/search/repositories", force=True)

    def test_raw_mode(self):
        c = _client(self.dir)
        resp = FakeResponse(b"# readme body")
        with mock.patch("urllib.request.urlopen", return_value=resp):
            text = c.get("http://x/repos/a/b/readme", force=True, raw=True)
        self.assertEqual(text, "# readme body")

    def test_rate_state_from_headers(self):
        c = _client(self.dir)
        headers = {"X-RateLimit-Remaining": "47", "X-RateLimit-Limit": "60",
                   "X-RateLimit-Reset": str(int(time.time()) + 300)}
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse({}, headers)):
            c.get("http://x/search/repositories", force=True)
        self.assertEqual(c.rate.remaining, 47)
        self.assertEqual(c.rate.limit, 60)
        self.assertFalse(c.rate.low(10))
        self.assertIn("47", c.rate.label())

    def test_auth_header_sent(self):
        c = _client(self.dir)
        c.cfg.token = "secret-token"

        class _Resp(FakeResponse):
            def __init__(self, *a, **kw):
                super().__init__({"ok": 1})
        with mock.patch("urllib.request.urlopen",
                        side_effect=_Resp) as m:
            c.get("http://x/search/repositories", force=True)
            req = m.call_args[0][0]
            self.assertEqual(req.get_header("Authorization"), "token secret-token")


if __name__ == "__main__":
    unittest.main()
