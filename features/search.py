# features/search.py - Search logic: query building, filters, history.

import difflib
import json
import os
import time

from config import DATA_DIR

HISTORY_FILE = os.path.join(DATA_DIR, "search_history.json")
MAX_ENTRIES = 50

FILTER_KEYS = (
    "language", "stars", "forks", "created", "pushed", "topic",
    "license", "archived", "is", "user", "org", "in", "size", "fork",
)


def build_query(term, filters=None):
    """term + {key: value} -> GitHub search query string."""
    parts = [term.strip()] if term and term.strip() else []
    for key, value in (filters or {}).items():
        if value:
            parts.append("%s:%s" % (key, value))
    return " ".join(parts)


def complete_filter_key(prefix):
    """Tab-completion candidates for filter builder."""
    prefix = prefix.lower()
    return [k for k in FILTER_KEYS if k.startswith(prefix)]


class SearchHistory:
    """Persistent search history: [{"q": ..., "ts": ...}], newest first."""

    def __init__(self, path=HISTORY_FILE):
        self.path = path
        self.entries = []
        self._load()

    def _load(self):
        try:
            with open(self.path) as f:
                data = json.load(f)
            self.entries = [e for e in data if isinstance(e, dict) and e.get("q")][:MAX_ENTRIES]
        except (OSError, ValueError):
            self.entries = []

    def save(self):
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(self.path, "w") as f:
                json.dump(self.entries, f, indent=2)
        except OSError:
            pass

    def add(self, query):
        query = query.strip()
        if not query:
            return
        self.entries = [e for e in self.entries if e["q"] != query]
        self.entries.insert(0, {"q": query, "ts": time.time()})
        del self.entries[MAX_ENTRIES:]
        self.save()

    def delete(self, index):
        if 0 <= index < len(self.entries):
            del self.entries[index]
            self.save()

    def clear(self):
        self.entries = []
        self.save()

    def recall(self, prefix, limit=10):
        """Fuzzy recall: substring first, then difflib similarity."""
        prefix = prefix.strip().lower()
        if not prefix:
            return [e["q"] for e in self.entries[:limit]]
        exact = [e["q"] for e in self.entries if prefix in e["q"].lower()]
        rest = [e["q"] for e in self.entries if prefix not in e["q"].lower()]
        ranked = sorted(rest, key=lambda q: -difflib.SequenceMatcher(None, prefix, q.lower()).ratio())
        return (exact + ranked)[:limit]
