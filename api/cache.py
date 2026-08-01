# api/cache.py - In-memory LRU TTL cache + on-disk JSON cache.

import hashlib
import json
import os
import shutil
import time
from collections import OrderedDict


class MemoryCache:
    """LRU dict cache with per-entry TTL."""

    def __init__(self, max_entries=200):
        self.max_entries = max_entries
        self._data = OrderedDict()

    def get(self, key):
        entry = self._data.get(key)
        if entry is None:
            return None
        value, expires = entry
        if expires is not None and time.time() > expires:
            del self._data[key]
            return None
        self._data.move_to_end(key)
        return value

    def set(self, key, value, ttl=None):
        expires = time.time() + ttl if ttl else None
        self._data[key] = (value, expires)
        self._data.move_to_end(key)
        while len(self._data) > self.max_entries:
            self._data.popitem(last=False)

    def clear(self):
        self._data.clear()

    def __len__(self):
        return len(self._data)


class DiskCache:
    """JSON files on disk keyed by URL sha1; ttl in seconds."""

    def __init__(self, directory):
        self.directory = directory

    def _path(self, key):
        return os.path.join(self.directory, hashlib.sha1(key.encode("utf-8")).hexdigest() + ".json")

    def get(self, key, ttl=None):
        path = self._path(key)
        try:
            with open(path) as f:
                entry = json.load(f)
            if ttl is None:
                ttl = entry.get("ttl")
            if ttl and time.time() - entry["fetched_at"] > ttl:
                return None
            return entry["data"]
        except (OSError, ValueError, KeyError):
            return None

    def set(self, key, value, ttl=None):
        try:
            os.makedirs(self.directory, exist_ok=True)
            entry = {"fetched_at": time.time(), "ttl": ttl, "data": value}
            tmp = self._path(key) + ".tmp"
            with open(tmp, "w") as f:
                json.dump(entry, f)
            os.replace(tmp, self._path(key))
        except OSError:
            pass

    def clear(self):
        try:
            if os.path.isdir(self.directory):
                shutil.rmtree(self.directory)
        except OSError:
            pass


class Cache:
    """Combined memory + disk cache. Disabled entirely when cache_enabled=False."""

    def __init__(self, directory, enabled=True, max_entries=200):
        self.enabled = enabled
        self.memory = MemoryCache(max_entries)
        self.disk = DiskCache(directory)

    def get(self, key, ttl=None):
        if not self.enabled:
            return None
        value = self.memory.get(key)
        if value is not None:
            return value
        value = self.disk.get(key, ttl)
        if value is not None:
            self.memory.set(key, value, ttl)
        return value

    def set(self, key, value, ttl=None):
        if not self.enabled:
            return
        self.memory.set(key, value, ttl)
        self.disk.set(key, value, ttl)

    def clear(self):
        self.memory.clear()
        self.disk.clear()
