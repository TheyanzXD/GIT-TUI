# ui/keys.py - Key binding registry: defaults + user overrides + dispatcher.

import curses
import json
import os

from config import DATA_DIR

KEYBIND_FILE = os.path.join(DATA_DIR, "keybindings.json")

# action -> description, shown in help modal
ACTIONS = {
    "quit": "Quit / go back",
    "help": "Help modal",
    "panel": "Switch panel focus",
    "palette": "Command palette",
    "refresh": "Force refresh view",
    "up": "Move up",
    "down": "Move down",
    "top": "Jump to top",
    "bottom": "Jump to bottom",
    "page_up": "Half page up",
    "page_down": "Half page down",
    "open": "Open selected",
    "search_focus": "Focus search input",
    "filter_builder": "Open filter builder",
    "cycle_sort": "Cycle sort field",
    "toggle_order": "Toggle sort order",
    "history": "Search history",
    "bookmark": "Toggle bookmark",
    "clone": "Clone repository",
    "browser": "Open in browser",
    "copy_url": "Copy URL to clipboard",
    "select": "Toggle batch selection",
    "section_next": "Next detail section",
    "section_prev": "Previous detail section",
    "back": "Go back",
    "clear_cache": "Clear cache",
    "settings": "Settings menu",
    "trending": "Trending view",
    "user_view": "Open user profile",
    "bookmarks_view": "Bookmarks view",
    "export_list": "Export list (CSV/Markdown)",
    "clone_queue": "Clone queue",
    "history_delete": "Delete history entry",
    "history_clear": "Clear all history",
    "exit": "Quit immediately",
}

DEFAULT_BINDINGS = {
    "global": {
        "q": "back", "esc": "back", "?": "help", "tab": "panel", ":": "palette",
        "ctrl-r": "refresh", "ctrl-c": "exit", "x": "settings",
    },
    "list": {
        "down": "down", "j": "down", "up": "up", "k": "up", "g": "top", "home": "top",
        "G": "bottom", "end": "bottom", "pgdn": "page_down", "pgup": "page_up",
        "enter": "open", "c": "clone", "b": "bookmark", "o": "browser", "y": "copy_url",
        " ": "select", "/": "search_focus", "f": "filter_builder", "s": "cycle_sort",
        "O": "toggle_order", "h": "history", "t": "trending", "u": "user_view",
        "B": "bookmarks_view", "e": "export_list", "n": "clone_queue",
        "d": "history_delete", "D": "history_clear",
    },
    "detail": {
        "tab": "section_next", "shift-tab": "section_prev", "c": "clone",
        "b": "bookmark", "o": "browser", "y": "copy_url",
    },
}

_KEY_NAMES = {
    curses.KEY_UP: "up", curses.KEY_DOWN: "down", curses.KEY_LEFT: "left",
    curses.KEY_RIGHT: "right", curses.KEY_HOME: "home", curses.KEY_END: "end",
    curses.KEY_NPAGE: "pgdn", curses.KEY_PPAGE: "pgup",
}


class KeyBindings:
    """Resolve getch() codes -> action strings. Loads user overrides from file."""

    def __init__(self, path=KEYBIND_FILE):
        self.sections = {k: dict(v) for k, v in DEFAULT_BINDINGS.items()}
        self._load(path)

    def _load(self, path):
        try:
            with open(path) as f:
                user = json.load(f)
        except (OSError, ValueError):
            self._write_defaults(path)
            return
        for section, mapping in user.items():
            if section in self.sections and isinstance(mapping, dict):
                self.sections[section].update({k: str(v) for k, v in mapping.items()})

    def _write_defaults(self, path):
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(path, "w") as f:
                json.dump(DEFAULT_BINDINGS, f, indent=2)
        except OSError:
            pass

    def resolve(self, section, keycode):
        """keycode int -> action name or None."""
        if keycode in (10, 13):
            key = "enter"
        elif keycode == 27:
            key = "esc"
        elif keycode == 9:
            key = "tab"
        elif keycode in (353,):  # shift-tab (backtab)
            key = "shift-tab"
        elif keycode == 32:
            key = " "
        elif keycode in _KEY_NAMES:
            key = _KEY_NAMES[keycode]
        elif 0 <= keycode < 32:
            key = "ctrl-%s" % chr(keycode + 96)
        else:
            try:
                key = chr(keycode)
            except ValueError:
                return None
        mapping = self.sections.get(section) or self.sections["global"]
        return mapping.get(key)

    def help_lines(self):
        """[(section, [(key, action)])] for the help modal."""
        lines = []
        for section, mapping in DEFAULT_BINDINGS.items():
            rows = []
            for key, action in mapping.items():
                desc = ACTIONS.get(action, action)
                rows.append((key.replace("ctrl-", "Ctrl+").replace("-", "+"), desc))
            lines.append((section, rows))
        return lines
