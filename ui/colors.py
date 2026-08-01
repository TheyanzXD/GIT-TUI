# ui/colors.py - Color pair definitions and theme management.

import curses

# Logical pair IDs used across the app.
PAIR_GREEN = 1
PAIR_SELECTED = 2
PAIR_CYAN = 3
PAIR_YELLOW = 4
PAIR_RED = 5
PAIR_MAGENTA = 6
PAIR_HEADER = 7
PAIR_BADGE = 8
PAIR_OK = 9
PAIR_ERR = 10

THEMES = {
    "default": {
        PAIR_GREEN: (curses.COLOR_GREEN, -1),
        PAIR_SELECTED: (curses.COLOR_WHITE, curses.COLOR_BLUE),
        PAIR_CYAN: (curses.COLOR_CYAN, -1),
        PAIR_YELLOW: (curses.COLOR_YELLOW, -1),
        PAIR_RED: (curses.COLOR_RED, -1),
        PAIR_MAGENTA: (curses.COLOR_MAGENTA, -1),
        PAIR_HEADER: (curses.COLOR_WHITE, curses.COLOR_BLACK),
        PAIR_BADGE: (curses.COLOR_BLACK, curses.COLOR_YELLOW),
        PAIR_OK: (curses.COLOR_WHITE, curses.COLOR_GREEN),
        PAIR_ERR: (curses.COLOR_WHITE, curses.COLOR_RED),
    },
    "high_contrast": {
        PAIR_GREEN: (curses.COLOR_GREEN, -1),
        PAIR_SELECTED: (curses.COLOR_WHITE, curses.COLOR_RED),
        PAIR_CYAN: (curses.COLOR_WHITE, -1),
        PAIR_YELLOW: (curses.COLOR_YELLOW, -1),
        PAIR_RED: (curses.COLOR_RED, -1),
        PAIR_MAGENTA: (curses.COLOR_MAGENTA, -1),
        PAIR_HEADER: (curses.COLOR_BLACK, curses.COLOR_WHITE),
        PAIR_BADGE: (curses.COLOR_WHITE, curses.COLOR_YELLOW),
        PAIR_OK: (curses.COLOR_WHITE, curses.COLOR_GREEN),
        PAIR_ERR: (curses.COLOR_WHITE, curses.COLOR_RED),
    },
    "minimal": {
        PAIR_GREEN: (curses.COLOR_GREEN, -1),
        PAIR_SELECTED: (curses.COLOR_WHITE, curses.COLOR_BLUE),
        PAIR_CYAN: (curses.COLOR_CYAN, -1),
        PAIR_YELLOW: (curses.COLOR_YELLOW, -1),
        PAIR_RED: (curses.COLOR_RED, -1),
        PAIR_MAGENTA: (curses.COLOR_CYAN, -1),
        PAIR_HEADER: (curses.COLOR_CYAN, -1),
        PAIR_BADGE: (curses.COLOR_CYAN, -1),
        PAIR_OK: (curses.COLOR_GREEN, -1),
        PAIR_ERR: (curses.COLOR_RED, -1),
    },
}

# 256-color boost when available.
_BOOST_256 = {
    PAIR_CYAN: 39,
    PAIR_MAGENTA: 213,
    PAIR_YELLOW: 220,
    PAIR_GREEN: 82,
}


def init_colors(stdscr, theme="default"):
    """Initialize color pairs for theme. Safe on any terminal; returns bool has_color."""
    theme = theme if theme in THEMES else "default"
    has = False
    try:
        has = curses.has_colors()
        if has:
            curses.start_color()
            curses.use_default_colors()
            pairs = THEMES[theme]
            if curses.COLORS >= 256:
                pairs = {k: v for k, v in pairs.items()}
                boosted = {}
                for k, (fg, bg) in pairs.items():
                    if k in _BOOST_256 and bg == -1:
                        boosted[k] = (_BOOST_256[k], -1)
                    else:
                        boosted[k] = (fg, bg)
                pairs = boosted
            for pair_id, (fg, bg) in pairs.items():
                try:
                    curses.init_pair(pair_id, fg, bg)
                except Exception:
                    pass
    except Exception:
        has = False
    return has
