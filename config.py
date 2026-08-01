# config.py - Configuration loading, defaults, and persistence.

import json
import os

DATA_DIR = os.path.join(os.path.expanduser("~"), ".github_tui")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

DEFAULTS = {
    "token": "",
    "default_sort": "stars",
    "default_order": "desc",
    "clone_dir": os.path.expanduser("~/projects"),
    "clone_protocol": "https",
    "editor": "",
    "color_theme": "default",
    "date_format": "relative",
    "per_page": 30,
    "mouse_support": True,
    "unicode_borders": True,
    "show_clock": True,
    "cache_enabled": True,
}

SORTS = ("stars", "forks", "updated", "name")
ORDERS = ("desc", "asc")
THEMES = ("default", "high_contrast", "minimal")


class Config:
    """Dict-backed config with defaults, file persistence, and CLI overrides."""

    token: str
    default_sort: str
    default_order: str
    clone_dir: str
    clone_protocol: str
    editor: str
    color_theme: str
    date_format: str
    per_page: int
    mouse_support: bool
    unicode_borders: bool
    show_clock: bool
    cache_enabled: bool

    def __init__(self, data=None):
        self.data = dict(DEFAULTS)
        if data:
            self.data.update({k: v for k, v in data.items() if k in DEFAULTS})

    def __getattr__(self, name):
        try:
            return self.data[name]
        except KeyError:
            raise AttributeError(name)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        if key not in DEFAULTS:
            raise KeyError("unknown config key: %s" % key)
        self.data[key] = value
        self.save()

    def save(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.data, f, indent=2)
        except OSError:
            pass

    @classmethod
    def load(cls, overrides=None):
        data = {}
        try:
            with open(CONFIG_FILE) as f:
                data = json.load(f)
        except (OSError, ValueError):
            data = {}
        cfg = cls(data)
        if overrides:
            cfg.data.update({k: v for k, v in overrides.items() if k in DEFAULTS})
        if cfg.token == "":
            cfg.token = os.environ.get("GITHUB_TOKEN", "")
        return cfg

    def apply_cli(self, kwargs):
        """Merge CLI flag overrides (only keys present in DEFAULTS)."""
        for k, v in kwargs.items():
            if v is not None and k in DEFAULTS:
                self.data[k] = v
        return self
