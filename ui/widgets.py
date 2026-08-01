# ui/widgets.py - Reusable UI components: list, scrollbar, spinner, progress, modal, flash.

import time

import curses

from ui import colors
from utils import truncate

ASCII = False


def set_ascii_mode(value):
    global ASCII
    ASCII = value


def _box_chars(style):
    if ASCII:
        return ("+", "-", "+", "+", "|", "+", "+")
    return {
        "rounded": ("╭", "─", "╮", "│", "╰", "─", "╯"),
        "single": ("┌", "─", "┐", "│", "└", "─", "┘"),
        "double": ("╔", "═", "╗", "║", "╚", "═", "╝"),
        "bold": ("┏", "━", "┓", "┃", "┗", "━", "┛"),
    }[style]


def draw_box(win, y, x, h, w, style="rounded", pair=colors.PAIR_CYAN):
    """Draw a bordered box on win; returns inner (y, x, h, w) rect."""
    if h < 2 or w < 2:
        return (y, x, max(0, h - 2), max(0, w - 2))
    tl, hc, tr, vc, bl, hc2, br = _box_chars(style)
    try:
        attr = curses.color_pair(pair)
    except Exception:
        attr = 0
    try:
        win.addch(y, x, tl, attr)
        win.addch(y, x + w - 1, tr, attr)
        win.addch(y + h - 1, x, bl, attr)
        win.addch(y + h - 1, x + w - 1, br, attr)
        for cx in range(x + 1, x + w - 1):
            win.addch(y, cx, hc, attr)
            win.addch(y + h - 1, cx, hc2, attr)
        for cy in range(y + 1, y + h - 1):
            win.addch(cy, x, vc, attr)
            win.addch(cy, x + w - 1, vc, attr)
    except Exception:
        pass
    return (y + 1, x + 1, h - 2, w - 2)


class ListBox:
    """Scrollable list with viewport, half-page paging, batch selection, scrollbar."""

    def __init__(self, rows=None):
        self.rows = rows or []
        self.selected = 0
        self.top = 0
        self.multi = set()

    def set_rows(self, rows):
        self.rows = rows
        if self.selected >= len(self.rows):
            self.selected = max(0, len(self.rows) - 1)

    def clamp(self, viewport_h):
        if self.selected < self.top:
            self.top = self.selected
        elif self.selected >= self.top + viewport_h:
            self.top = self.selected - viewport_h + 1

    def move(self, delta, viewport_h):
        new = self.selected + delta
        self.selected = max(0, min(len(self.rows) - 1 if self.rows else 0, new))
        self.clamp(viewport_h)

    def page(self, delta, viewport_h):
        self.move(delta * max(1, viewport_h // 2), viewport_h)

    def top_jump(self, viewport_h):
        self.selected = 0
        self.clamp(viewport_h)

    def bottom_jump(self, viewport_h):
        self.selected = len(self.rows) - 1 if self.rows else 0
        self.clamp(viewport_h)

    def toggle_multi(self):
        if 0 <= self.selected < len(self.rows):
            if self.selected in self.multi:
                self.multi.discard(self.selected)
            else:
                self.multi.add(self.selected)

    def _scrollbar(self, viewport_h):
        total = len(self.rows)
        if total <= viewport_h or viewport_h <= 0:
            return None
        thumb = max(1, int(viewport_h * viewport_h / total))
        max_start = max(0, total - viewport_h)
        track = viewport_h - thumb
        start = int(self.top * track / max_start) if max_start else 0
        return (start, thumb)

    def render(self, win, y, x, h, w, focused=True, row_pair=None):
        """row_pair(i, selected, focused) -> pair id (or None for default)."""
        if h <= 0 or w <= 0:
            return
        has_multi = len(self.multi) > 0
        for line in range(h):
            idx = self.top + line
            if idx >= len(self.rows):
                break
            text = self.rows[idx]
            selected = idx == self.selected
            if has_multi:
                marker = "▣ " if idx in self.multi else ("▢ " if not ASCII else "# ")
            else:
                marker = ""
            text = truncate(text, max(0, w - len(marker)))
            if selected and focused:
                pair = colors.PAIR_SELECTED
            elif row_pair:
                pair = row_pair(idx, selected, focused) or colors.PAIR_GREEN
            else:
                pair = colors.PAIR_GREEN
            try:
                win.addstr(y + line, x, marker + text, curses.color_pair(pair))
            except Exception:
                try:
                    win.addstr(y + line, x, truncate(text, max(0, w - 1)), curses.color_pair(pair))
                except Exception:
                    pass
        sb = self._scrollbar(h)
        if sb:
            start, thumb = sb
            try:
                for i in range(h):
                    ch = "█" if not ASCII else "#"
                    win.addch(y + i, x + w - 1, ch if start <= i < start + thumb else "│",
                              curses.color_pair(colors.PAIR_CYAN))
            except Exception:
                pass


class Spinner:
    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    FALLBACK = ["-", "\\", "|", "/"]

    def __init__(self):
        self._start = time.time()

    def frame(self, now=None):
        now = now if now is not None else time.time()
        frames = self.FALLBACK if ASCII else self.FRAMES
        return frames[int((now - self._start) * 10) % len(frames)]

    def reset(self):
        self._start = time.time()


def render_progress(win, y, x, w, frac):
    if w <= 0:
        return
    filled = int(round(max(0.0, min(1.0, frac)) * w))
    if ASCII:
        text = "#" * filled + "-" * (w - filled)
    else:
        text = "█" * filled + "░" * (w - filled)
    try:
        win.addstr(y, x, text, curses.color_pair(colors.PAIR_CYAN))
    except Exception:
        pass


class Modal:
    """Centered floating dialogs: text, input, confirm, help, error."""

    def __init__(self, stdscr):
        self.stdscr = stdscr

    def _box(self, title, width, height, style="double"):
        max_y, max_x = self.stdscr.getmaxyx()
        height = min(height, max_y)
        width = min(width, max_x)
        y = max(0, (max_y - height) // 2)
        x = max(0, (max_x - width) // 2)
        inner = draw_box(self.stdscr, y, x, height, width, style)
        if title:
            try:
                t = truncate(title, max(0, width - 4))
                attr = curses.color_pair(colors.PAIR_HEADER) | curses.A_BOLD
                self.stdscr.addstr(y, x + 2, " %s " % t, attr)
            except Exception:
                pass
        return inner

    def text(self, title, lines, footer=None):
        """Show lines, wait for any key. Returns when key pressed."""
        inner_y, inner_x, inner_h, inner_w = self._box(title, 76, 20)
        try:
            attr = curses.color_pair(colors.PAIR_CYAN) | curses.A_BOLD
            self.stdscr.addstr(inner_y, inner_x,
                               truncate(lines[0], inner_w) if lines else "", attr)
            for i, line in enumerate(lines[1:], start=1):
                if i >= inner_h:
                    break
                pair = colors.PAIR_GREEN
                self.stdscr.addstr(inner_y + i, inner_x,
                                   truncate(line, inner_w), curses.color_pair(pair))
            if footer:
                fy = inner_y + inner_h - 1
                attr2 = curses.color_pair(colors.PAIR_MAGENTA)
                self.stdscr.addstr(fy, inner_x, truncate(footer, inner_w), attr2)
        except Exception:
            pass
        self.stdscr.refresh()
        while True:
            key = self.stdscr.getch()
            if key != -1:
                return key

    def input_prompt(self, title, initial="", secret=False, width=60, hint=None, on_tab=None):
        """Blocking text input. Returns entered string ('' on Esc).

        on_tab(buf) -> replacement text (e.g. tab completion); None disables Tab.
        """
        self.stdscr.timeout(-1)
        self.stdscr.keypad(1)
        max_y, max_x = self.stdscr.getmaxyx()
        width = min(width, max_x - 4)
        inner_y, inner_x, inner_h, inner_w = self._box(title, width + 2, 5)
        buf = list(initial)
        while True:
            line = "*" * len(buf) if secret else "".join(buf)
            line = truncate(line, inner_w - 1)
            try:
                self.stdscr.addstr(inner_y + 1, inner_x, line + " " * (inner_w - 1 - len(line)),
                                   curses.color_pair(colors.PAIR_GREEN))
                hint_text = truncate(hint or "Enter=ok  Esc=cancel", inner_w - 1)
                self.stdscr.addstr(inner_y + 3, inner_x, hint_text, curses.color_pair(colors.PAIR_MAGENTA))
            except Exception:
                pass
            self.stdscr.move(inner_y + 1, inner_x + len(line))
            self.stdscr.refresh()
            key = self.stdscr.getch()
            if key in (10, 13):
                return "".join(buf)
            if key in (27,):
                return ""
            if key == 9 and on_tab:
                buf = list(on_tab("".join(buf)))
            elif key in (8, 127, curses.KEY_BACKSPACE if hasattr(curses, "KEY_BACKSPACE") else 127):
                if buf:
                    buf.pop()
            elif 32 <= key < 127:
                if len(buf) < inner_w - 1:
                    buf.append(chr(key))

    def confirm(self, question, title="Confirm"):
        """Yes/no dialog. Returns bool."""
        self._box(title, max(40, len(question) + 8), 5)
        max_y, max_x = self.stdscr.getmaxyx()
        cy = max_y // 2
        cx = max(0, (max_x - len(question)) // 2)
        try:
            self.stdscr.addstr(cy, cx, truncate(question, max_x - 1), curses.color_pair(colors.PAIR_YELLOW))
            self.stdscr.addstr(cy + 2, cx, "[y] Yes   [n] No", curses.color_pair(colors.PAIR_MAGENTA))
        except Exception:
            pass
        self.stdscr.refresh()
        while True:
            key = self.stdscr.getch()
            if key in (ord("y"), ord("Y"), 10, 13):
                return True
            if key in (ord("n"), ord("N"), 27):
                return False

    def error(self, message):
        self.text("Error", [message], footer="Press any key to continue")

    def help(self, lines):
        """lines: [(section_title, [(key, desc)])]."""
        rows = []
        for section, items in lines:
            rows.append("── %s ──" % section)
            for key, desc in items:
                rows.append("  %-10s %s" % (key, desc))
        self.text("Help", rows, footer="Press any key to close")


class FlashMessage:
    def __init__(self, msg="", kind="info", duration=2.0):
        self.msg = msg
        self.kind = kind
        self.expires = time.time() + duration

    @property
    def live(self):
        return time.time() < self.expires

    def pair(self):
        return {
            "success": colors.PAIR_OK,
            "warning": colors.PAIR_BADGE,
            "error": colors.PAIR_ERR,
            "info": colors.PAIR_CYAN,
        }[self.kind]
