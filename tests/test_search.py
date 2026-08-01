import os
import shutil
import tempfile
import unittest

from features.search import SearchHistory, build_query, complete_filter_key


class TestQuery(unittest.TestCase):
    def test_build_query(self):
        self.assertEqual(build_query("flask", {"language": "python", "stars": ">500"}),
                         "flask language:python stars:>500")

    def test_build_query_empty(self):
        self.assertEqual(build_query("", {}), "")

    def test_complete_filter_key(self):
        self.assertEqual(complete_filter_key("la"), ["language"])
        self.assertIn("stars", complete_filter_key("st"))
        self.assertEqual(complete_filter_key("zzz"), [])


class TestSearchHistory(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "history.json")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_add_dedupe(self):
        h = SearchHistory(self.path)
        h.add("flask")
        h.add("django")
        h.add("flask")
        self.assertEqual(len(h.entries), 2)
        self.assertEqual(h.entries[0]["q"], "flask")

    def test_max_entries(self):
        h = SearchHistory(self.path)
        for i in range(60):
            h.add("q%d" % i)
        self.assertEqual(len(h.entries), 50)
        self.assertEqual(h.entries[0]["q"], "q59")

    def test_delete_clear(self):
        h = SearchHistory(self.path)
        h.add("a")
        h.add("b")
        h.delete(0)
        self.assertEqual([e["q"] for e in h.entries], ["a"])
        h.clear()
        self.assertEqual(h.entries, [])

    def test_persist(self):
        h = SearchHistory(self.path)
        h.add("flask")
        h2 = SearchHistory(self.path)
        self.assertEqual([e["q"] for e in h2.entries], ["flask"])

    def test_recall(self):
        h = SearchHistory(self.path)
        for q in ["django rest", "django admin", "flask tutorial"]:
            h.add(q)
        recalled = h.recall("django")
        self.assertEqual(recalled[:2], ["django admin", "django rest"])
        self.assertEqual(len(h.recall("")), 3)

    def test_empty_recall(self):
        h = SearchHistory(self.path)
        self.assertEqual(h.recall("x"), [])


if __name__ == "__main__":
    unittest.main()
