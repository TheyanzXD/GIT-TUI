# features/trending.py - Scrape github.com/trending with API fallback.

import datetime
from html.parser import HTMLParser

from api import endpoints


def _parse_count(text):
    text = text.strip().replace(",", "").lower()
    mult = 1
    if text.endswith("k"):
        mult = 1000
        text = text[:-1]
    elif text.endswith("m"):
        mult = 1000000
        text = text[:-1]
    try:
        return int(float(text) * mult)
    except ValueError:
        return 0


class _TrendingParser(HTMLParser):
    """Extract repo rows from github.com/trending HTML."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.repos = []
        self._cur = None
        self._h2 = False
        self._desc = False
        self._lang = False
        self._link_href = None
        self._link_text = []
        self._links = []
        self._lang_text = ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "article":
            self._cur = {"full_name": "", "description": "", "stars": 0, "forks": 0,
                         "language": "", "today": 0}
            self._links = []
        if self._cur is None:
            return
        if tag == "h2":
            self._h2 = True
        elif tag == "p" and not self._h2:
            self._desc = True
        elif tag == "a":
            self._link_href = a.get("href", "")
            self._link_text = []
        elif tag == "span" and a.get("itemprop") == "programmingLanguage":
            self._lang = True
            self._lang_text = ""

    def handle_endtag(self, tag):
        if self._cur is None:
            return
        if tag == "article":
            self._finalize()
            self._cur = None
        elif tag == "h2":
            self._h2 = False
        elif tag == "p":
            self._desc = False
        elif tag == "a":
            if self._link_href is not None:
                self._links.append((self._link_href, "".join(self._link_text).strip()))
            self._link_href = None
        elif tag == "span":
            self._lang = False

    def handle_data(self, data):
        if self._cur is None:
            return
        if self._h2 and self._link_href:
            self._link_text.append(data)
        elif self._desc and self._link_href is None:
            self._cur["description"] += data.strip()
        elif self._link_href is not None:
            self._link_text.append(data)
        elif self._lang:
            self._lang_text += data

    def _finalize(self):
        if self._cur is None:
            return
        cur = self._cur
        for href, text in self._links:
            if href.startswith("/") and "/" in href[1:] and not href.endswith("/stargazers") \
                    and not href.endswith("/forks") and not href.endswith("/issues") \
                    and not href.endswith("/security") and "/tree/" not in href and "/blob/" not in href:
                cur["full_name"] = href.strip("/")
                cur["name"] = href.rstrip("/").rsplit("/", 1)[-1]
            elif href.endswith("/stargazers"):
                cur["stars"] = _parse_count(text)
            elif href.endswith("/forks"):
                cur["forks"] = _parse_count(text)
            if "stars today" in text:
                cur["today"] = _parse_count(text.split("stars today")[0])
        cur["language"] = self._lang_text.strip()
        if cur["full_name"]:
            cur["html_url"] = "https://github.com/%s" % cur["full_name"]
            self.repos.append(cur)


def scrape_trending(client, since="daily", language=None, spoken=None):
    url = endpoints.trending(since, language, spoken)
    html = client.get(url, ttl=1800, raw=True,
                      extra_headers={"Accept": "text/html,application/xhtml+xml"})
    parser = _TrendingParser()
    try:
        parser.feed(html)
    except Exception:
        return []
    return parser.repos


def api_fallback(client, since="daily", language=None, per_page=30):
    days = {"daily": 1, "weekly": 7, "monthly": 30}.get(since, 7)
    created = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    q = "created:>%s" % created
    if language:
        q += " language:%s" % language
    data = client.get(endpoints.search_repos(q, sort="stars", per_page=per_page), ttl=1800)
    return [{
        "full_name": r.get("full_name"),
        "name": r.get("name"),
        "description": r.get("description") or "",
        "stars": r.get("stargazers_count", 0),
        "forks": r.get("forks_count", 0),
        "language": r.get("language") or "",
        "today": 0,
        "html_url": r.get("html_url"),
    } for r in data.get("items", [])]


def fetch_trending(client, since="daily", language=None, spoken=None):
    """Trending repos as list of dicts. Falls back to search API on any failure."""
    try:
        repos = scrape_trending(client, since, language, spoken)
        if repos:
            return repos
    except Exception:
        pass
    return api_fallback(client, since, language)
