# ui/layout.py - Panel layout manager with dynamic resizing and borders.

import curses

from ui import colors
from ui.widgets import draw_box, set_ascii_mode

MIN_COLS_FOR_SIDEBAR = 80
MIN_ROWS_FOR_FULL_HEADER = 24


class Layout:
    """Computes panel rects from terminal size; draws borders and headers."""

    def __init__(self, stdscr, cfg):
        self.stdscr = stdscr
        self.cfg = cfg
        self.unicode_ok = self._probe_unicode()
        set_ascii_mode(not self.unicode_ok)
        self.update()

    def _probe_unicode(self):
        if not self.cfg.unicode_borders:
            return False
        try:
            self.stdscr.addstr(0, 0, "╭")
            return True
        except Exception:
            return False

    def update(self):
        rows, cols = self.stdscr.getmaxyx()
        self.rows, self.cols = rows, cols
        header_h = 3 if rows >= MIN_ROWS_FOR_FULL_HEADER else 1
        status_h = 2 if rows >= 10 else 1
        sidebar_w = int(cols * 0.30) if cols >= MIN_COLS_FOR_SIDEBAR else 0
        sidebar_w = max(24, sidebar_w) if sidebar_w else 0
        sidebar_w = min(sidebar_w, 40)
        main_w = max(0, cols - sidebar_w)
        self.header = (0, 0, header_h, cols)
        self.sidebar = (header_h, 0, max(0, rows - header_h - status_h), sidebar_w) if sidebar_w else None
        self.main = (header_h, sidebar_w, max(0, rows - header_h - status_h), main_w)
        self.status = (rows - status_h, 0, status_h, cols)

    def rect(self, name):
        return getattr(self, name)

    def border(self, rect, style="rounded", active=False, title=None):
        y, x, h, w = rect
        if h <= 0 or w <= 0:
            return
        if active:
            style = "bold"
        inner = draw_box(self.stdscr, y, x, h, w, style)
        if title:
            try:
                t = title[: max(0, w - 4)]
                self.stdscr.addstr(y, x + 2, " %s " % t,
                                   curses.color_pair(colors.PAIR_CYAN) | curses.A_BOLD)
            except Exception:
                pass
        return inner

    def text(self, rect, y_offset, x_offset, text, pair=colors.PAIR_GREEN, attr=0):
        y, x, h, w = rect
        try:
            self.stdscr.addstr(y + y_offset, x + x_offset, text[: max(0, w - x_offset - 1)],
                               curses.color_pair(pair) | attr)
        except Exception:
            pass

    def clear_rect(self, rect):
        y, x, h, w = rect
        try:
            self.stdscr.addstr(y, x, " " * w)
            for i in range(1, h):
                self.stdscr.addstr(y + i, x, " " * w)
        except Exception:
            pass
