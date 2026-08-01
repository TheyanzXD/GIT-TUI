import os
import shutil
import tempfile
import time
import unittest

from api.cache import MemoryCache, DiskCache, Cache


class TestMemoryCache(unittest.TestCase):
    def test_get_set(self):
        c = MemoryCache(10)
        c.set("a", 1)
        self.assertEqual(c.get("a"), 1)
        self.assertIsNone(c.get("missing"))

    def test_lru_eviction(self):
        c = MemoryCache(2)
        c.set("a", 1)
        c.set("b", 2)
        c.set("c", 3)
        self.assertIsNone(c.get("a"))
        self.assertEqual(c.get("b"), 2)
        self.assertEqual(c.get("c"), 3)

    def test_ttl_expiry(self):
        c = MemoryCache(10)
        c.set("a", 1, ttl=0.05)
        self.assertEqual(c.get("a"), 1)
        time.sleep(0.1)
        self.assertIsNone(c.get("a"))

    def test_clear(self):
        c = MemoryCache(10)
        c.set("a", 1)
        c.clear()
        self.assertIsNone(c.get("a"))


class TestDiskCache(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_roundtrip(self):
        d = DiskCache(self.dir)
        d.set("url1", {"x": 1})
        self.assertEqual(d.get("url1"), {"x": 1})

    def test_ttl(self):
        d = DiskCache(self.dir)
        d.set("url1", {"x": 1}, ttl=0.05)
        time.sleep(0.1)
        self.assertIsNone(d.get("url1"))

    def test_corrupt_file_safe(self):
        d = DiskCache(self.dir)
        os.makedirs(self.dir, exist_ok=True)
        with open(os.path.join(self.dir, "deadbeef.json"), "w") as f:
            f.write("{not json")
        self.assertIsNone(d.get("url1"))

    def test_clear(self):
        d = DiskCache(self.dir)
        d.set("url1", {"x": 1})
        d.clear()
        self.assertIsNone(d.get("url1"))


class TestCache(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_memory_hit_avoids_disk(self):
        c = Cache(self.dir)
        c.set("k", "v")
        c.disk.set = lambda *a: self.fail("disk set called")
        self.assertEqual(c.get("k"), "v")

    def test_disk_backfill(self):
        c = Cache(self.dir)
        d2 = Cache(self.dir)
        c.set("k", "v")
        self.assertEqual(d2.get("k"), "v")

    def test_disabled(self):
        c = Cache(self.dir, enabled=False)
        c.set("k", "v")
        self.assertIsNone(c.get("k"))


if __name__ == "__main__":
    unittest.main()
