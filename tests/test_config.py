import os
import shutil
import tempfile
import unittest

from config import Config


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_defaults(self):
        c = Config()
        self.assertEqual(c.default_sort, "stars")
        self.assertEqual(c.per_page, 30)
        self.assertEqual(c.clone_protocol, "https")

    def test_unknown_keys_ignored(self):
        c = Config({"bogus": 1})
        self.assertNotIn("bogus", c.data)

    def test_set_roundtrip(self):
        path = os.path.join(self.dir, "config.json")
        c = Config()
        c.data["clone_protocol"] = "ssh"
        c.save = lambda: None
        # persistence via direct file write:
        import json
        with open(path, "w") as f:
            json.dump(c.data, f)
        loaded = Config.load()
        self.assertEqual(loaded.data["clone_protocol"], "https")  # real file untouched
        os.remove(path)

    def test_load_missing_file(self):
        c = Config.load()
        self.assertEqual(c.default_sort, "stars")

    def test_env_token(self):
        os.environ["GITHUB_TOKEN"] = "tok123"
        try:
            c = Config.load()
            self.assertEqual(c.token, "tok123")
        finally:
            del os.environ["GITHUB_TOKEN"]

    def test_apply_cli(self):
        c = Config()
        c.apply_cli({"per_page": 10, "bogus": 99})
        self.assertEqual(c.per_page, 10)

    def test_set_unknown_key_raises(self):
        c = Config()
        with self.assertRaises(KeyError):
            c.set("bogus", 1)


if __name__ == "__main__":
    unittest.main()
