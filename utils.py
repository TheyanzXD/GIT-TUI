# utils.py - Shared helpers: formatting, markdown stripping, misc.

import datetime
import logging
import os
import re
import shutil
import subprocess
import sys

LOG_FILE = os.path.join(os.path.expanduser("~"), ".github_tui", "debug.log")


def setup_logging(debug=False):
    if not debug and not os.environ.get("DEBUG"):
        return None
    try:
        logging.basicConfig(
            filename=LOG_FILE,
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        return logging.getLogger("github-tui")
    except OSError:
        return None


def truncate(text, width):
    """Truncate text to width, preserving single-line terminal safety."""
    if text is None:
        return ""
    text = str(text)
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width == 1:
        return "…" if len(text) > 1 else text
    return text[: width - 1] + "…"


def format_number(n):
    """1234 -> '1.2k', 3400000 -> '3.4M'."""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "0"
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        return "%.1fk" % (n / 1000)
    return "%.1fM" % (n / 1_000_000)


def _parse_iso(iso):
    if not iso:
        return None
    try:
        return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None


def time_ago(iso, now=None):
    """ISO timestamp -> '2h ago' (or '-')."""
    dt = _parse_iso(iso)
    if dt is None:
        return "-"
    now = now or datetime.datetime.now(datetime.timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    delta = now - dt
    secs = int(delta.total_seconds())
    if secs < 0:
        secs = 0
    if secs < 60:
        return "%ds ago" % secs
    if secs < 3600:
        return "%dm ago" % (secs // 60)
    if secs < 86400:
        return "%dh ago" % (secs // 3600)
    if secs < 86400 * 30:
        return "%dd ago" % (secs // 86400)
    return "%dmo ago" % (secs // (86400 * 30))


def format_date(iso, relative=False):
    dt = _parse_iso(iso)
    if dt is None:
        return "-"
    if relative:
        return time_ago(iso)
    return dt.strftime("%Y-%m-%d")


def parse_repo_spec(text):
    """'owner/repo' -> (owner, repo); raises ValueError on bad format."""
    parts = text.strip().strip("/").split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError("expected OWNER/REPO")
    return parts[0], parts[1]


# --- Markdown -> plain text (for README rendering) ---

_CODE_BLOCK_RE = re.compile(r"```(\w*)\n?(.*?)```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)
_LIST_RE = re.compile(r"^\s*[-*+]\s+", re.MULTILINE)
_NUM_RE = re.compile(r"^\s*\d+\.\s+", re.MULTILINE)
_IMG_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_QUOTE_RE = re.compile(r"^\s*>\s?", re.MULTILINE)


def markdown_to_text(md, code_blocks=None):
    """Strip markdown to readable plain text. Code blocks collected separately.

    code_blocks: optional list; (lang, code) tuples appended in order.
    """
    text = md or ""
    text = _CODE_BLOCK_RE.sub(
        lambda m: (code_blocks.append((m.group(1), m.group(2)))
                   or "[code block: %s]" % (m.group(1) or "text")), text)
    text = _IMG_RE.sub("", text)
    text = _LINK_RE.sub(r"\1", text)
    text = _INLINE_CODE_RE.sub(r"\1", text)
    text = _HEADING_RE.sub(lambda m: m.group(2).upper(), text)
    text = _LIST_RE.sub("  - ", text)
    text = _NUM_RE.sub("  ", text)
    text = _QUOTE_RE.sub("  ", text)
    text = _HTML_TAG_RE.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[*_~]{1,3}([^*_~]+)[*_~]{1,3}", r"\1", text)
    return text.strip()


# --- misc ---

def copy_to_clipboard(text):
    """Copy text via platform clipboard tool. Returns bool."""
    for cmd in (["termux-clipboard-set"], ["pbcopy"], ["xclip", "-selection", "c"], ["wl-copy"]):
        try:
            subprocess.run(cmd, input=text, text=True, timeout=3, check=True)
            return True
        except (OSError, subprocess.SubprocessError):
            continue
    return False


def open_browser(url):
    """Open URL in the platform browser. Returns bool."""
    if sys.platform.startswith("linux") and shutil.which("termux-open-url"):
        cmd = ["termux-open-url", url]
    else:
        cmd = ["xdg-open", url]
    try:
        subprocess.Popen(cmd)
        return True
    except OSError:
        return False


def bar(frac, width):
    """Horizontal bar with block chars (ascii fallback for narrow/old terms)."""
    if width <= 0:
        return ""
    filled = int(round(frac * width))
    filled = max(0, min(width, filled))
    return "█" * filled + "░" * (width - filled)


def languages_bar(langs, width=30):
    """[(name, fraction)] -> [(name, label, bar_str)] for rendering."""
    out = []
    for name, frac in langs:
        label = "%s %5.1f%%" % (name, frac * 100)
        out.append((name, label, bar(frac, width)))
    return out


def safe_ascii(text):
    """Replace unsupported wide chars with ASCII when needed (terminal check)."""
    return text


def supports_unicode(stdscr):
    """Best-effort detection of unicode-capable terminal."""
    if not hasattr(stdscr, "getmaxyx"):
        return True
    try:
        stdscr.addstr(0, 0, "█")
        return True
    except Exception:
        return False
