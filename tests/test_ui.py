import unittest

import curses

from ui.keys import KeyBindings
from ui.layout import Layout
from ui.widgets import ListBox, Spinner, render_progress, draw_box
from config import Config


def setUpModule():
    """Emulate an initialized curses terminal so color_pair() is safe in tests."""
    if not getattr(curses, "_test_color_patched", False):
        curses.color_pair = lambda n: n << 8
        curses._test_color_patched = True


class FakeScreen:
    """Minimal curses screen double recording calls."""

    def __init__(self, rows=24, cols=80, keys=None):
        self.rows, self.cols = rows, cols
        self.calls = []
        self.keys = list(keys or [])
        self._timeout = -1

    def getmaxyx(self):
        return self.rows, self.cols

    def addstr(self, y, x, s, attr=0):
        self.calls.append(("addstr", y, x, str(s)))

    def addch(self, y, x, ch, attr=0):
        self.calls.append(("addch", y, x, ch))

    def refresh(self):
        pass

    def getch(self):
        return self.keys.pop(0) if self.keys else -1

    def move(self, y, x):
        self.calls.append(("move", y, x))

    def timeout(self, v):
        self._timeout = v

    def keypad(self, v):
        pass

    def erase(self):
        pass


class TestListBox(unittest.TestCase):
    def setUp(self):
        self.box = ListBox([str(i) for i in range(50)])

    def test_move_bounds(self):
        self.box.move(-5, 10)
        self.assertEqual(self.box.selected, 0)
        self.box.move(1000, 10)
        self.assertEqual(self.box.selected, 49)

    def test_clamp_keeps_selected_visible(self):
        self.box.selected = 45
        self.box.clamp(10)
        self.assertEqual(self.box.top, 36)
        self.box.selected = 39
        self.box.clamp(10)
        self.assertEqual(self.box.top, 36)

    def test_page_half(self):
        self.box.move(10, 10)
        self.box.page(1, 10)
        self.assertEqual(self.box.selected, 15)

    def test_home_end(self):
        self.box.selected = 25
        self.box.top_jump(10)
        self.assertEqual(self.box.selected, 0)
        self.box.bottom_jump(10)
        self.assertEqual(self.box.selected, 49)

    def test_multi_toggle(self):
        self.box.selected = 3
        self.box.toggle_multi()
        self.assertIn(3, self.box.multi)
        self.box.toggle_multi()
        self.assertNotIn(3, self.box.multi)

    def test_scrollbar_none_when_fits(self):
        small = ListBox(["a", "b", "c"])
        self.assertIsNone(small._scrollbar(5))

    def test_render_no_crash(self):
        screen = FakeScreen()
        self.box.render(screen, 1, 1, 10, 30)
        self.assertTrue(screen.calls)

    def test_render_does_not_exceed_height(self):
        screen = FakeScreen()
        self.box.render(screen, 0, 0, 10, 30)
        for kind, y, *_ in screen.calls:
            if kind == "addstr":
                self.assertLess(y, 10)


class TestLayout(unittest.TestCase):
    def _lay(self, rows, cols):
        return Layout(FakeScreen(rows, cols), Config())

    def test_wide_terminal_sidebar(self):
        lay = self._lay(30, 100)
        self.assertIsNotNone(lay.sidebar)
        self.assertGreaterEqual(lay.sidebar[3], 24)

    def test_narrow_terminal_no_sidebar(self):
        lay = self._lay(30, 70)
        self.assertIsNone(lay.sidebar)
        self.assertEqual(lay.main[1], 0)

    def test_short_terminal_collapsed_header(self):
        lay = self._lay(20, 100)
        self.assertEqual(lay.header[2], 1)

    def test_full_terminal_header(self):
        lay = self._lay(30, 100)
        self.assertEqual(lay.header[2], 3)

    def test_rects_cover_screen(self):
        lay = self._lay(30, 100)
        self.assertEqual(lay.header[2] + lay.sidebar[2] + lay.status[2], 30)
        self.assertEqual(lay.main[3] + lay.sidebar[3], 100)

    def test_resize_update(self):
        screen = FakeScreen(30, 100)
        lay = Layout(screen, Config())
        screen.rows, screen.cols = 20, 60
        lay.update()
        self.assertEqual(lay.header[2], 1)
        self.assertIsNone(lay.sidebar)


class TestKeyBindings(unittest.TestCase):
    def test_resolve_common(self):
        kb = KeyBindings("/nonexistent.json")
        self.assertEqual(kb.resolve("list", ord("j")), "down")
        self.assertEqual(kb.resolve("list", 10), "open")
        self.assertEqual(kb.resolve("list", curses.KEY_DOWN), "down")
        self.assertEqual(kb.resolve("list", curses.KEY_PPAGE), "page_up")
        self.assertEqual(kb.resolve("global", 27), "back")
        self.assertEqual(kb.resolve("global", ord("q")), "back")
        self.assertEqual(kb.resolve("global", 18), "refresh")  # ctrl-r

    def test_detail_section(self):
        kb = KeyBindings("/nonexistent.json")
        self.assertEqual(kb.resolve("detail", 9), "section_next")
        self.assertEqual(kb.resolve("detail", 353), "section_prev")

    def test_user_overrides(self):
        import json
        import os
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"list": {"j": "top"}}, f)
            path = f.name
        try:
            kb = KeyBindings(path)
            self.assertEqual(kb.resolve("list", ord("j")), "top")
        finally:
            os.unlink(path)

    def test_help_lines(self):
        kb = KeyBindings("/nonexistent.json")
        lines = kb.help_lines()
        self.assertEqual(len(lines), 3)
        actions = [action for _, rows in lines for _, action in rows]
        self.assertIn("Go back", actions)
        self.assertIn("Force refresh view", actions)


class TestModal(unittest.TestCase):
    def test_input_prompt_returns_text(self):
        screen = FakeScreen(keys=[ord("a"), ord("b"), 10])
        from ui.widgets import Modal
        m = Modal(screen)
        self.assertEqual(m.input_prompt("T"), "ab")

    def test_input_prompt_esc_cancels(self):
        screen = FakeScreen(keys=[27])
        from ui.widgets import Modal
        m = Modal(screen)
        self.assertEqual(m.input_prompt("T"), "")

    def test_input_backspace(self):
        screen = FakeScreen(keys=[ord("a"), ord("b"), 8, 10])
        from ui.widgets import Modal
        self.assertEqual(Modal(screen).input_prompt("T"), "a")

    def test_confirm(self):
        from ui.widgets import Modal
        screen = FakeScreen(keys=[ord("n")])
        self.assertFalse(Modal(screen).confirm("q?"))
        screen = FakeScreen(keys=[ord("y")])
        self.assertTrue(Modal(screen).confirm("q?"))

    def test_text_returns_on_key(self):
        from ui.widgets import Modal
        screen = FakeScreen(keys=[ord("x")])
        self.assertEqual(Modal(screen).text("t", ["line"]), ord("x"))


class TestMisc(unittest.TestCase):
    def test_spinner_frames(self):
        s = Spinner()
        f = s.frame(now=0.0)
        self.assertIn(f, Spinner.FRAMES)

    def test_draw_box_small(self):
        screen = FakeScreen()
        inner = draw_box(screen, 0, 0, 1, 1)
        self.assertEqual(inner, (0, 0, 0, 0))

    def test_render_progress(self):
        screen = FakeScreen()
        render_progress(screen, 0, 0, 10, 0.5)
        self.assertTrue(screen.calls)


if __name__ == "__main__":
    unittest.main()
