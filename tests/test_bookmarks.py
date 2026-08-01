import os
import shutil
import tempfile
import unittest

from features.bookmarks import BookmarkManager


class TestBookmarks(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "bookmarks.json")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_add_toggle_remove(self):
        b = BookmarkManager(self.path)
        self.assertTrue(b.add("a/b", stars=10))
        self.assertFalse(b.add("a/b", stars=10))  # dup
        self.assertTrue(b.is_bookmarked("a/b"))
        self.assertFalse(b.toggle("a/b"))  # removes
        self.assertFalse(b.is_bookmarked("a/b"))
        self.assertTrue(b.toggle("a/b", stars=5))  # re-adds

    def test_collections(self):
        b = BookmarkManager(self.path)
        b.add("a/b", collection="ml")
        self.assertTrue(b.is_bookmarked("a/b", "ml"))
        self.assertFalse(b.is_bookmarked("a/b", "default"))
        self.assertIn("ml", b.collections_list())

    def test_persist(self):
        b = BookmarkManager(self.path)
        b.add("a/b", stars=3)
        b2 = BookmarkManager(self.path)
        self.assertTrue(b2.is_bookmarked("a/b"))

    def test_export_markdown(self):
        b = BookmarkManager(self.path)
        b.add("a/b", stars=3)
        out = os.path.join(self.dir, "out.md")
        b.export_markdown(out)
        with open(out) as f:
            content = f.read()
        self.assertIn("a/b", content)
        self.assertIn("https://github.com/a/b", content)

    def test_import_json(self):
        b = BookmarkManager(self.path)
        b.add("a/b", stars=3)
        src = os.path.join(self.dir, "src.json")
        shutil.copy(self.path, src)
        b2 = BookmarkManager(os.path.join(self.dir, "other.json"))
        count = b2.import_json(src)
        self.assertEqual(count, 1)
        self.assertTrue(b2.is_bookmarked("a/b"))


if __name__ == "__main__":
    unittest.main()
