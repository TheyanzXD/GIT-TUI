# features/bookmarks.py - Bookmark CRUD with named collections.

import json
import os
import time
from typing import Any, Dict, List

from config import DATA_DIR

BOOKMARK_FILE = os.path.join(DATA_DIR, "bookmarks.json")


class BookmarkManager:
    """{collections: {name: [{full_name, stars, ts}]}}."""

    def __init__(self, path=BOOKMARK_FILE):
        self.path = path
        self.collections: Dict[str, List[Dict[str, Any]]] = {"default": []}
        self._load()

    def _load(self):
        try:
            with open(self.path) as f:
                data = json.load(f)
            cols = data.get("collections", data if isinstance(data, dict) else {})
            self.collections = {k: list(v) for k, v in cols.items() if isinstance(v, list)}
            if "default" not in self.collections:
                self.collections["default"] = []
        except (OSError, ValueError):
            self.collections = {"default": []}

    def save(self):
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(self.path, "w") as f:
                json.dump({"collections": self.collections}, f, indent=2)
        except OSError:
            pass

    def is_bookmarked(self, full_name, collection="default"):
        return any(b["full_name"] == full_name for b in self.collections.get(collection, []))

    def add(self, full_name, stars=0, collection="default"):
        if collection not in self.collections:
            self.collections[collection] = []
        if self.is_bookmarked(full_name, collection):
            return False
        self.collections[collection].append(
            {"full_name": full_name, "stars": int(stars or 0), "ts": time.time()})
        self.save()
        return True

    def remove(self, full_name, collection="default"):
        col = self.collections.get(collection, [])
        new = [b for b in col if b["full_name"] != full_name]
        changed = len(new) != len(col)
        if changed:
            self.collections[collection] = new
            self.save()
        return changed

    def toggle(self, full_name, stars=0, collection="default"):
        if self.is_bookmarked(full_name, collection):
            self.remove(full_name, collection)
            return False
        self.add(full_name, stars, collection)
        return True

    def list_collection(self, collection="default"):
        return self.collections.get(collection, [])

    def collections_list(self):
        return [c for c, items in self.collections.items() if items]

    def export_markdown(self, path):
        lines = ["# GitHub Bookmarks\n"]
        for name, items in self.collections.items():
            if not items:
                continue
            lines.append("## %s\n" % name)
            for b in sorted(items, key=lambda x: -x["stars"]):
                lines.append("- [%s](https://github.com/%s) ⭐ %s\n" % (
                    b["full_name"], b["full_name"], b["stars"]))
        with open(path, "w") as f:
            f.writelines(lines)
        return path

    def import_json(self, path):
        with open(path) as f:
            data = json.load(f)
        cols = data.get("collections", data if isinstance(data, dict) else {})
        count = 0
        for name, items in cols.items():
            for b in items:
                if isinstance(b, dict) and b.get("full_name"):
                    if self.add(b["full_name"], b.get("stars", 0), name):
                        count += 1
        return count
