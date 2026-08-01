import unittest

from utils import (truncate, format_number, time_ago, format_date, parse_repo_spec,
                   markdown_to_text, bar, languages_bar)


class TestUtils(unittest.TestCase):
    def test_truncate(self):
        self.assertEqual(truncate("hello", 10), "hello")
        self.assertEqual(truncate("hello world", 5), "hell…")
        self.assertEqual(truncate("hello", 1), "…")
        self.assertEqual(truncate(None, 5), "")
        self.assertEqual(truncate("x", 0), "")

    def test_format_number(self):
        self.assertEqual(format_number(0), "0")
        self.assertEqual(format_number(999), "999")
        self.assertEqual(format_number(1234), "1.2k")
        self.assertEqual(format_number(3400000), "3.4M")
        self.assertEqual(format_number(None), "0")

    def test_time_ago(self):
        self.assertEqual(time_ago(""), "-")
        self.assertEqual(time_ago("garbage"), "-")
        self.assertTrue(time_ago("2020-01-01T00:00:00Z").endswith("ago"))

    def test_format_date(self):
        self.assertEqual(format_date(""), "-")
        self.assertEqual(format_date("2020-01-02T03:04:05Z"), "2020-01-02")
        self.assertTrue(format_date("2020-01-02T03:04:05Z", relative=True).endswith("ago"))

    def test_parse_repo_spec(self):
        self.assertEqual(parse_repo_spec("owner/repo"), ("owner", "repo"))
        self.assertEqual(parse_repo_spec("/owner/repo/"), ("owner", "repo"))
        with self.assertRaises(ValueError):
            parse_repo_spec("norepo")
        with self.assertRaises(ValueError):
            parse_repo_spec("a/b/c")

    def test_markdown_to_text(self):
        md = "# Title\n\nsome **bold** and [link](http://x)\n\n```py\nprint(1)\n```"
        blocks = []
        text = markdown_to_text(md, blocks)
        self.assertIn("TITLE", text)
        self.assertIn("some bold and link", text)
        self.assertIn("[code block: py]", text)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0][0], "py")

    def test_markdown_lists(self):
        md = "- item one\n- item two\n\n1. first\n2. second\n"
        text = markdown_to_text(md)
        self.assertIn("- item one", text)
        self.assertIn("first", text)

    def test_bar(self):
        self.assertEqual(bar(1.0, 4), "████")
        self.assertEqual(bar(0.0, 4), "░░░░")
        self.assertEqual(bar(0.5, 4), "██░░")
        self.assertEqual(bar(1.0, 0), "")

    def test_languages_bar(self):
        out = languages_bar([("Python", 0.5)], 10)
        self.assertEqual(len(out), 1)
        name, label, bar_str = out[0]
        self.assertEqual(name, "Python")
        self.assertEqual(len(bar_str), 10)


if __name__ == "__main__":
    unittest.main()
