# app.py - Main application controller and event loop.

import csv
import datetime
import re
import time
from typing import List, Optional

import curses

from api import endpoints
from api.client import GitHubClient, GitHubError, RateLimitError, NetworkError, NotFoundError
from api.models import Repo, User, Org, Commit, Issue, Release, Contributor
from config import Config, DATA_DIR
from features.bookmarks import BookmarkManager
from features.clone import CloneManager
from features.search import SearchHistory, build_query, complete_filter_key
from features.trending import fetch_trending
from ui import colors
from ui.keys import KeyBindings
from ui.layout import Layout
from ui.widgets import ListBox, Modal, Spinner, FlashMessage, render_progress, ASCII
from utils import (truncate, format_number, time_ago, format_date, parse_repo_spec,
                   copy_to_clipboard, open_browser, markdown_to_text, languages_bar)

DETAIL_TABS = ["Overview", "README", "Files", "Commits", "Issues",
               "Releases", "Contributors", "Languages"]
MENU = [("t", "Trending"), ("/", "Search"), ("B", "Bookmarks"),
        ("h", "History"), ("u", "User"), ("x", "Settings"), ("q", "Quit")]


def err_text(e):
    if isinstance(e, RateLimitError):
        s = e.reset_ts - int(time.time()) if e.reset_ts else 0
        m, s = divmod(max(0, s), 60)
        return "Rate limit reached — resets in %dm %ds" % (m, s)
    return e.message


class ListView:
    """A scrollable list: search results, trending, bookmarks, history, user repos."""

    def __init__(self, kind, title, loader):
        self.kind = kind
        self.title = title
        self.loader = loader      # (page, append) -> (rows, data, err)
        self.box = ListBox()
        self.data = []
        self.page = 1
        self.force = False
        self.query = ""
        self.filters = {}
        self.sort = "stars"
        self.order = "desc"
        self.loaded_at = None
        self.trending_opts = {}

    def load(self, append=False):
        rows, data, err = self.loader(self.page, append, self.force)
        if append:
            self.box.rows += rows
            self.data += data
        else:
            self.box.set_rows(rows)
            self.data = data
        self.force = False
        self.loaded_at = time.time()
        return err


class DetailView:
    """Repository detail with tabbed sections."""

    def __init__(self, app, repo):
        self.app = app
        self.repo = repo
        self.tab = 0
        self.box = ListBox()
        self.meta = []            # per-row: None | dict(url=..., type=..., path=...)
        self.pairs = []           # per-row color pair
        self.error = None
        self.rows = []
        self.expanded = set()
        self.tree: Optional[List[dict]] = None
        self.commits_page = 1
        self.issues_page = 1
        self.releases_page = 1
        self.loaded = set()

    @property
    def name(self):
        return self.repo.full_name

    @property
    def title(self):
        return self.repo.full_name

    def ensure(self):
        if self.tab in self.loaded:
            return
        self.error = None
        try:
            rows, meta, pairs = self._load_tab(self.tab)
            self.box.set_rows(rows)
            self.meta = meta
            self.pairs = pairs
            self.loaded.add(self.tab)
        except GitHubError as e:
            self.box.set_rows([])
            self.meta = []
            self.pairs = []
            self.error = err_text(e)

    def _load_tab(self, tab):
        name = DETAIL_TABS[tab]
        app = self.app
        cl = app.client
        c = self.repo
        if name == "Overview":
            d = cl.get(endpoints.repo(c.owner, c.name), ttl=600, force=app.force_all)
            repo = Repo.from_dict(d)
            rows = [
                repo.description or "(no description)",
                "",
                "Homepage: %s" % (repo.homepage or "-"),
                "License: %s   Branch: %s   Archived: %s" % (
                    repo.license or "-", repo.default_branch, "yes" if repo.archived else "no"),
                "Topics: " + (" ".join("#" + t for t in repo.topics) if repo.topics else "-"),
                "",
                "Stars: %d   Forks: %d   Watchers: %d   Open issues: %d" % (
                    repo.stargazers_count, repo.forks_count,
                    repo.watchers_count, repo.open_issues_count),
                "Created: %s   Pushed: %s" % (
                    format_date(repo.created_at), time_ago(repo.pushed_at)),
            ]
            pairs = [colors.PAIR_GREEN] * len(rows)
            pairs[4] = colors.PAIR_BADGE
            return rows, [None] * len(rows), pairs
        if name == "README":
            md = cl.get(endpoints.readme(c.owner, c.name), ttl=3600,
                        force=app.force_all, raw=True,
                        extra_headers={"Accept": "application/vnd.github.v3.raw"})
            blocks: List[str] = []
            text = markdown_to_text(md, blocks)
            rows, pairs = [], []
            block_iter = iter(blocks)
            for line in text.splitlines():
                if line.startswith("[code block:"):
                    try:
                        lang, code = next(block_iter)
                    except StopIteration:
                        continue
                    if lang:
                        rows.append("  " + lang)
                        pairs.append(colors.PAIR_MAGENTA)
                    for cline in code.splitlines():
                        rows.append("  " + cline)
                        pairs.append(colors.PAIR_CYAN)
                else:
                    rows.append(line)
                    pairs.append(colors.PAIR_GREEN)
            if not rows:
                rows = ["(no README)"]
                pairs = [colors.PAIR_YELLOW]
            return rows, [None] * len(rows), pairs
        if name == "Files":
            if self.tree is None:
                d = cl.get(endpoints.tree(c.owner, c.name), ttl=600, force=app.force_all)
                entries = [e for e in d.get("tree", []) if e.get("type") in ("blob", "tree")]
                entries.sort(key=lambda e: (e.get("type") != "tree", e.get("path", "")))
                self.tree = entries
            rows, meta, pairs = [], [], []
            for e in self.tree:
                path = e.get("path", "")
                depth = path.count("/")
                if depth:
                    ancestors = [path.split("/")[i] for i in range(depth)]
                    prefix = ""
                    skip = False
                    for a in ancestors:
                        prefix = prefix + "/" + a if prefix else a
                        if prefix not in self.expanded:
                            skip = True
                            break
                    if skip:
                        continue
                is_dir = e.get("type") == "tree"
                icon = "▸ " if is_dir and not ASCII else ("▾ " if is_dir else "  ")
                size = "" if is_dir else "  %s" % format_file_size(e.get("size", 0))
                rows.append("  " * depth + icon + path.rsplit("/", 1)[-1] + size)
                meta.append({"type": "dir" if is_dir else "file", "path": path})
                pairs.append(colors.PAIR_CYAN if is_dir else colors.PAIR_GREEN)
            return rows, meta, pairs
        if name == "Commits":
            d = cl.get(endpoints.commits(c.owner, c.name, page=self.commits_page,
                                         per_page=app.cfg.per_page), ttl=300,
                       force=app.force_all)
            commits = [Commit.from_dict(x) for x in d]
            rows = ["%s  %s  %s  %s" % (cm.sha, cm.author, time_ago(cm.date), cm.message)
                    for cm in commits]
            return rows, [{"url": cm.html_url, "type": "url"} for cm in commits], \
                [colors.PAIR_GREEN] * len(rows)
        if name == "Issues":
            d = cl.get(endpoints.issues(c.owner, c.name, page=self.issues_page,
                                        per_page=app.cfg.per_page, labels=app.issue_label),
                       ttl=300, force=app.force_all)
            issues = [Issue.from_dict(x) for x in d]
            rows = ["#%d %s  [%s]  %s  (%s)" % (
                i.number, i.title, ",".join(i.labels) or "-", i.author, time_ago(i.created_at))
                for i in issues]
            return rows, [{"url": i.html_url, "type": "url"} for i in issues], \
                [colors.PAIR_GREEN] * len(rows)
        if name == "Releases":
            d = cl.get(endpoints.releases(c.owner, c.name, page=self.releases_page,
                                          per_page=app.cfg.per_page), ttl=300,
                       force=app.force_all)
            rels = [Release.from_dict(x) for x in d]
            rows, meta, pairs = [], [], []
            for r in rels:
                rows.append("%s  (%s)  %d assets" % (
                    r.tag_name, format_date(r.published_at), r.assets))
                meta.append({"url": r.html_url, "type": "url"})
                pairs.append(colors.PAIR_CYAN)
                if r.body:
                    rows.append("   " + r.body)
                    meta.append(None)
                    pairs.append(colors.PAIR_GREEN)
            return rows, meta, pairs
        if name == "Contributors":
            d = cl.get(endpoints.contributors(c.owner, c.name), ttl=600, force=app.force_all)
            contribs = [Contributor.from_dict(x) for x in d]
            rows = ["(%s) %s — %d commits" % (
                x.login[:1].upper(), x.login, x.contributions) for x in contribs]
            return rows, [None] * len(rows), [colors.PAIR_GREEN] * len(rows)
        if name == "Languages":
            d = cl.get(endpoints.languages(c.owner, c.name), ttl=600, force=app.force_all)
            if not isinstance(d, dict) or not d:
                return ["(no language data)"], [None], [colors.PAIR_YELLOW]
            total = float(sum(d.values()))
            langs = sorted(((k, v / total) for k, v in d.items()), key=lambda x: -x[1])[:10]
            width = min(30, max(10, self.app.layout.main[3] // 3))
            rows, pairs = [], []
            for name_l, frac in langs:
                label = "%s  %5.1f%%" % (name_l, frac * 100)
                rows.append("%-20s %s" % (label, languages_bar([(name_l, frac)], width)[0][2]))
                pairs.append(colors.PAIR_CYAN)
            return rows, [None] * len(rows), pairs
        raise ValueError("unknown tab")

    def open_row(self):
        """Enter on a row: open URL in browser or toggle tree dir."""
        idx = self.box.selected
        if idx >= len(self.meta):
            return
        m = self.meta[idx]
        if not m:
            return
        if m.get("type") == "dir":
            path = m["path"]
            if path in self.expanded:
                self.expanded.discard(path)
            else:
                self.expanded.add(path)
            self.loaded.discard(self.tab)
            self.ensure()
            return
        if m.get("type") == "file":
            app = self.app
            try:
                d = app.client.get(endpoints.commits(self.repo.owner, self.repo.name,
                                                     per_page=1, path=m["path"]), ttl=300)
                if d:
                    cm = Commit.from_dict(d[0])
                    app.flash = FlashMessage("%s: %s" % (cm.sha, cm.message), "info", 3)
                else:
                    app.flash = FlashMessage("no commits for this file", "info")
            except GitHubError as e:
                app.flash = FlashMessage(err_text(e), "error")
            return
        if m.get("url"):
            if not open_browser(m["url"]):
                self.app.flash = FlashMessage("no browser available", "warning")

    def _page_next(self):
        """Fetch next page of the current list-style section."""
        if DETAIL_TABS[self.tab] == "Commits":
            self.commits_page += 1
        elif DETAIL_TABS[self.tab] == "Issues":
            self.issues_page += 1
        else:
            self.releases_page += 1
        try:
            rows, meta, pairs = self._load_tab(self.tab)
        except GitHubError as e:
            self.app.flash = FlashMessage(err_text(e), "error")
            return
        if not rows:
            self.app.flash = FlashMessage("no more data", "info")
            return
        self.box.rows += rows
        self.meta += meta
        self.pairs += pairs


def format_file_size(n):
    try:
        n = int(n or 0)
    except (TypeError, ValueError):
        return "0B"
    if n < 1024:
        return "%dB" % n
    if n < 1024 * 1024:
        return "%.1fK" % (n / 1024)
    return "%.1fM" % (n / (1024 * 1024))


class App:
    def __init__(self, stdscr, cfg=None):
        self.stdscr = stdscr
        self.cfg = cfg or Config.load()
        self.client = GitHubClient(self.cfg)
        self.bookmarks = BookmarkManager()
        self.history = SearchHistory()
        self.clone = CloneManager(self.cfg)
        self.keys = KeyBindings()
        self.layout = Layout(stdscr, self.cfg)
        self.modal = Modal(stdscr)
        colors.init_colors(stdscr, self.cfg.color_theme)
        self.stack = []
        self.memory = {}
        self.flash = None
        self.spinner = Spinner()
        self.done = False
        self.offline = False
        self.force_all = False
        self.issue_label = ""
        self._last_render = 0.0
        self._start = time.time()
        if self.cfg.mouse_support:
            try:
                curses.mousemask(curses.ALL_MOUSE_EVENTS)
            except Exception:
                pass

    # ---------- view stack ----------

    def _key(self, view):
        return "%s|%s" % (view.kind, view.title)

    def push(self, view, save_scroll=True):
        if save_scroll:
            self._remember()
        self.stack.append(view)
        mem = self.memory.get(self._key(view))
        if mem and isinstance(view, ListView):
            view.box.selected, view.box.top = mem
        self.flash = None

    def _remember(self):
        if not self.stack:
            return
        v = self.stack[-1]
        if isinstance(v, ListView):
            self.memory[self._key(v)] = (v.box.selected, v.box.top)
        elif isinstance(v, DetailView):
            self.memory["detail|" + v.name] = (v.box.selected, v.box.top)

    def pop(self):
        if len(self.stack) <= 1:
            self.done = True
            return None
        self._remember()
        return self.stack.pop()

    @property
    def view(self):
        return self.stack[-1] if self.stack else None

    def breadcrumb(self):
        return " / ".join(
            v.title if isinstance(v, ListView) else v.name for v in self.stack[-3:])

    # ---------- loaders ----------

    def _search_loader(self, view):
        query = build_query(view.query, view.filters)

        def load(page, append, force):
            url = endpoints.search_repos(query, sort=view.sort, order=view.order,
                                         page=page, per_page=self.cfg.per_page)
            try:
                data = self.client.get(url, ttl=300, force=force)
            except GitHubError as e:
                self.offline = isinstance(e, NetworkError)
                return [], [], err_text(e)
            self.offline = False
            repos = [Repo.from_dict(d) for d in data.get("items", [])]
            rows = [self._repo_row(r) for r in repos]
            return rows, repos, None
        return load

    def _trending_loader(self, view):
        def load(page, append, force):
            try:
                raw = fetch_trending(self.client, **view.trending_opts)
            except GitHubError as e:
                self.offline = isinstance(e, NetworkError)
                return [], [], err_text(e)
            self.offline = False
            repos = []
            for r in raw:
                full = r["full_name"]
                parts = full.split("/")
                repos.append(Repo(
                    full_name=full,
                    name=r.get("name") or (parts[-1] if len(parts) > 1 else full),
                    owner=parts[0] if len(parts) > 1 else "",
                    description=r.get("description") or "",
                    html_url=r.get("html_url") or "",
                    stargazers_count=r.get("stars", 0),
                    forks_count=r.get("forks", 0),
                    language=r.get("language") or ""))
            rows = [self._repo_row(r) for r in repos]
            return rows, repos, None
        return load

    def _bookmarks_loader(self, view):
        def load(page, append, force):
            items = self.bookmarks.list_collection()
            rows = ["%s  ⭐%s" % (b["full_name"], format_number(b["stars"])) for b in items]
            return rows, items, None
        return load

    def _history_loader(self, view, prefix=""):
        def load(page, append, force):
            qs = self.history.recall(prefix)
            return qs, qs, None
        return load

    def _user_repos_loader(self, username, is_org):
        def load(page, append, force):
            ep = (endpoints.org_repos if is_org else endpoints.user_repos)(
                username, page=page, per_page=self.cfg.per_page)
            try:
                data = self.client.get(ep, ttl=300, force=force)
            except GitHubError as e:
                self.offline = isinstance(e, NetworkError)
                return [], [], err_text(e)
            self.offline = False
            repos = [Repo.from_dict(d) for d in data]
            return [self._repo_row(r) for r in repos], repos, None
        return load

    def _repo_row(self, r):
        return "%s  %-12s ⭐%s 🍴%s  %s" % (
            r.full_name, r.language or "-", format_number(r.stargazers_count),
            format_number(r.forks_count), time_ago(r.pushed_at))

    # ---------- actions ----------

    def load_view(self, view, append=False):
        err = view.load(append=append)
        if err:
            self.flash = FlashMessage(err, "error")
            if not view.box.rows:
                view.box.set_rows(["(%s)" % err])
        elif append:
            self.flash = FlashMessage("page %d loaded" % view.page, "success")
        return err

    def open_search(self, query, filters=None):
        self.history.add(query)
        view = ListView("search", "Search: %s" % query, None)
        view.query = query
        view.filters = filters or {}
        view.sort = self.cfg.default_sort
        view.order = self.cfg.default_order
        view.loader = self._search_loader(view)
        self.push(view)
        self.load_view(view)

    def open_trending(self, opts=None):
        view = ListView("trending", "Trending", None)
        view.trending_opts = opts or {}
        view.loader = self._trending_loader(view)
        self.push(view)
        self.load_view(view)

    def open_user(self, username):
        try:
            try:
                d = self.client.get(endpoints.user(username), ttl=600, force=self.force_all)
                u = User.from_dict(d)
                self.push(UserView(self, u, is_org=False))
            except NotFoundError:
                d = self.client.get(endpoints.org(username), ttl=600, force=self.force_all)
                self.push(UserView(self, Org.from_dict(d), is_org=True))
        except GitHubError as e:
            self.offline = isinstance(e, NetworkError)
            self.flash = FlashMessage(err_text(e), "error")

    def open_detail(self, repo):
        self._remember()
        d = DetailView(self, repo)
        mem = self.memory.get("detail|" + d.name)
        if mem:
            d.box.selected, d.box.top = mem
        self.stack.append(d)
        d.ensure()

    def clone_repo(self, repo):
        dest = self.modal.input_prompt(
            "Clone %s" % repo.full_name, initial=self.cfg.clone_dir,
            hint="dir (Enter=default)  Esc=cancel")
        if dest == "":
            dest = self.cfg.clone_dir
        self.flash = FlashMessage("cloning %s..." % repo.name, "info")
        self._render_once()
        last_pct = -1

        def on_line(line):
            nonlocal last_pct
            m = re.search(r"(\d+)%", line)
            if m:
                pct = int(m.group(1))
                if pct != last_pct:
                    last_pct = pct
                    self._render_progress(pct)

        try:
            code, target = self.clone.clone(repo, dest_dir=dest, on_line=on_line)
            if code == 0:
                self.flash = FlashMessage("cloned → %s" % target, "success")
            else:
                self.flash = FlashMessage("clone failed (dir exists or no network)", "error")
        except OSError:
            self.flash = FlashMessage("git not installed", "error")

    def clone_queue_menu(self):
        choice = self.modal.input_prompt(
            "Clone Queue (%d pending)" % len(self.clone.queue),
            hint="1 add current · 2 run queue · 3 clear · Esc cancel")
        v = self.view
        if isinstance(v, ListView) and v.box.selected < len(v.data):
            self.clone.add_to_queue(v.data[v.box.selected])
            self.flash = FlashMessage("queued (%d)" % len(self.clone.queue), "info")
        elif choice == "2":
            self.flash = FlashMessage("running queue (%d)..." % len(self.clone.queue), "info")
            self._render_once()
            results = self.clone.run_queue()
            ok = sum(1 for _, s in results if s)
            self.flash = FlashMessage("cloned %d/%d" % (ok, len(results)), "success")
        elif choice == "3":
            self.clone.queue = []
            self.flash = FlashMessage("queue cleared", "info")

    def export_list(self, view):
        rows = []
        cols = ("full_name", "stars", "language", "url")
        for d in view.data:
            if isinstance(d, Repo):
                rows.append([d.full_name, d.stargazers_count, d.language, d.html_url])
            elif isinstance(d, dict):
                rows.append([d.get("full_name", ""), d.get("stars", 0), "", d.get("html_url", "")])
        if not rows:
            self.flash = FlashMessage("nothing to export", "warning")
            return
        fmt = self.modal.input_prompt("Export (%d items)" % len(rows),
                                      initial="csv", hint="csv or md")
        fmt = fmt.lower().strip() or "csv"
        path = "%s/export_%s.%s" % (DATA_DIR, datetime.datetime.now().strftime("%Y%m%d_%H%M%S"), fmt)
        try:
            import os
            os.makedirs(DATA_DIR, exist_ok=True)
            if fmt == "md":
                with open(path, "w") as f:
                    f.write("# Exported\n")
                    for r in rows:
                        f.write("- %s (⭐%s)\n" % (r[0], r[1]))
            else:
                with open(path, "w", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(cols)
                    w.writerows(rows)
            self.flash = FlashMessage("exported %d → %s" % (len(rows), path), "success")
        except OSError as e:
            self.flash = FlashMessage("export failed: %s" % e, "error")

    def settings_menu(self):
        theme = self.cfg.color_theme
        self.modal.text("Settings", [
            "Theme: %s" % theme,
            "Clock: %s" % ("on" if self.cfg.show_clock else "off"),
            "Mouse: %s" % ("on" if self.cfg.mouse_support else "off"),
            "Cache: %s" % ("on" if self.cfg.cache_enabled else "off"),
            "Per page: %d" % self.cfg.per_page,
            "",
            "[1] clear cache   [2] cycle theme   [3] toggle clock",
            "[4] toggle mouse  [5] toggle cache",
        ], footer="Esc to close")
        choice = self.modal.input_prompt("Settings", hint="1-5, Esc")
        if choice == "1":
            self.client.cache.clear()
            self.flash = FlashMessage("cache cleared", "success")
        elif choice == "2":
            themes = ("default", "high_contrast", "minimal")
            self.cfg.color_theme = themes[(themes.index(theme) + 1) % len(themes)]
            self.cfg.save()
            colors.init_colors(self.stdscr, self.cfg.color_theme)
            self.flash = FlashMessage("theme: %s" % self.cfg.color_theme, "info")
        elif choice == "3":
            self.cfg.show_clock = not self.cfg.show_clock
            self.cfg.save()
        elif choice == "4":
            self.cfg.mouse_support = not self.cfg.mouse_support
            self.cfg.save()
        elif choice == "5":
            self.cfg.cache_enabled = not self.cfg.cache_enabled
            self.cfg.save()
            self.client.cache.enabled = self.cfg.cache_enabled

    def palette(self):
        hint = "search <q> | user <u> | view <o/r> | trending | bookmarks | settings | clear cache | quit"
        cmd = self.modal.input_prompt(":", initial="", hint=hint)
        self._palette_dispatch(cmd)

    def _palette_dispatch(self, cmd):
        parts = cmd.strip().split(maxsplit=1)
        if not parts:
            return
        verb, rest = parts[0].lower(), (parts[1] if len(parts) > 1 else "")
        if verb in ("search", "s") and rest:
            self.open_search(rest)
        elif verb in ("user", "u") and rest:
            self.open_user(rest)
        elif verb in ("view", "v", "repo") and rest:
            try:
                owner, name = parse_repo_spec(rest)
            except ValueError:
                self.flash = FlashMessage("expected OWNER/REPO", "error")
                return
            self.load_repo_by_name(owner, name)
        elif verb == "trending":
            self.open_trending()
        elif verb in ("bookmarks", "b"):
            self.open_bookmarks()
        elif verb in ("history", "h"):
            self.open_history()
        elif verb == "settings":
            self.settings_menu()
        elif verb == "clear" and rest.startswith("cache"):
            self.client.cache.clear()
            self.flash = FlashMessage("cache cleared", "success")
        elif verb in ("quit", "exit", "q"):
            self.done = True
        else:
            self.flash = FlashMessage("unknown command: %s" % cmd, "error")

    def load_repo_by_name(self, owner, name):
        try:
            d = self.client.get(endpoints.repo(owner, name), ttl=600)
            self.open_detail(Repo.from_dict(d))
        except GitHubError as e:
            self.offline = isinstance(e, NetworkError)
            self.flash = FlashMessage(err_text(e), "error")

    def open_bookmarks(self):
        view = ListView("bookmarks", "Bookmarks", None)
        view.loader = self._bookmarks_loader(view)
        self.push(view)

    def open_history(self):
        view = ListView("history", "Search History", None)
        view.loader = self._history_loader(view)
        self.push(view)

    def open_user_repos(self, username, is_org):
        view = ListView("user_repos", "%s repos" % username, None)
        view.loader = self._user_repos_loader(username, is_org)
        self.push(view)
        self.load_view(view)

    # ---------- key handling ----------

    def handle(self, action):
        v = self.view
        if action == "quit" or action == "back":
            self.pop()
            return
        if action == "exit":
            self.done = True
            return
        if action == "help":
            self.modal.help(self.keys.help_lines())
            return
        if action == "settings":
            self.settings_menu()
            return
        if action == "palette":
            self.palette()
            return
        if action == "refresh":
            self.force_all = True
            if isinstance(v, ListView):
                self.load_view(v)
            elif isinstance(v, DetailView):
                v.loaded = set()
                v.ensure()
            elif isinstance(v, UserView):
                v.reload()
            self.force_all = False
            self.flash = FlashMessage("refreshed", "success")
            return
        if isinstance(v, DetailView):
            self._detail_action(v, action)
        elif isinstance(v, UserView):
            self._user_action(v, action)
        else:
            self._list_action(v, action)

    def _list_action(self, v, action):
        box = v.box
        h = self.layout.main[2] - 2
        if action == "up":
            box.move(-1, h)
        elif action == "down":
            if box.selected >= len(box.rows) - 1 and v.kind in ("search", "user_repos") \
                    and not self.client.rate.low():
                v.page += 1
                self.load_view(v, append=True)
            else:
                box.move(1, h)
        elif action == "top":
            box.top_jump(h)
        elif action == "bottom":
            box.bottom_jump(h)
        elif action == "page_up":
            box.page(-1, h)
        elif action == "page_down":
            box.page(1, h)
        elif action == "select":
            box.toggle_multi()
        elif action == "open":
            self._open_item(v)
        elif action == "clone":
            self._clone_current(v)
        elif action == "bookmark":
            self._toggle_bookmark(v)
        elif action == "browser":
            self._browser_current(v)
        elif action == "copy_url":
            self._copy_current(v)
        elif action == "search_focus":
            if v.kind == "history":
                prefix = self.modal.input_prompt("Filter history", hint="prefix (Esc cancels)")
                if prefix is not None:
                    v.loader = self._history_loader(v, prefix)
                    self.load_view(v)
            else:
                self._search_prompt()
        elif action == "filter_builder":
            self._filter_prompt(v)
        elif action == "history_delete" and v.kind == "history":
            idx = v.box.selected
            if 0 <= idx < len(v.data):
                self.history.delete(idx)
                self.load_view(v)
        elif action == "history_clear" and v.kind == "history":
            if self.modal.confirm("Clear all history?"):
                self.history.clear()
                self.load_view(v)
        elif action == "cycle_sort" and v.kind == "search":
            sorts = ("stars", "forks", "updated", "name")
            v.sort = sorts[(sorts.index(v.sort) + 1) % len(sorts)]
            v.page = 1
            self.load_view(v)
            self.flash = FlashMessage("sort: %s" % v.sort, "info")
        elif action == "toggle_order" and v.kind == "search":
            v.order = "asc" if v.order == "desc" else "desc"
            v.page = 1
            self.load_view(v)
            self.flash = FlashMessage("order: %s" % v.order, "info")
        elif action == "history":
            self.open_history()
        elif action == "trending":
            self.open_trending()
        elif action == "user_view":
            u = self.modal.input_prompt("GitHub username")
            if u:
                self.open_user(u.strip())
        elif action == "bookmarks_view":
            self.open_bookmarks()
        elif action == "export_list":
            self.export_list(v)
        elif action == "clone_queue":
            self.clone_queue_menu()

    def _detail_action(self, v, action):
        box = v.box
        h = self.layout.main[2] - 3
        if action == "section_next":
            v.tab = (v.tab + 1) % len(DETAIL_TABS)
            v.ensure()
        elif action == "section_prev":
            v.tab = (v.tab - 1) % len(DETAIL_TABS)
            v.ensure()
        elif action == "up":
            box.move(-1, h)
        elif action == "down":
            if box.selected >= len(box.rows) - 1 and DETAIL_TABS[v.tab] in ("Commits", "Issues", "Releases"):
                v._page_next()
            else:
                box.move(1, h)
        elif action == "top":
            box.top_jump(h)
        elif action == "bottom":
            box.bottom_jump(h)
        elif action == "page_up":
            box.page(-1, h)
        elif action == "page_down":
            box.page(1, h)
        elif action == "open":
            v.open_row()
        elif action == "clone":
            self.clone_repo(v.repo)
        elif action == "bookmark":
            self._toggle_bookmark(v)
        elif action == "browser":
            if not open_browser(v.repo.html_url):
                self.flash = FlashMessage("no browser available", "warning")
        elif action == "copy_url":
            self._copy_current(v)

    def _user_action(self, v, action):
        if action == "open":
            self.open_user_repos(v.user.login, v.is_org)
        elif action == "browser":
            if not open_browser(v.user.html_url):
                self.flash = FlashMessage("no browser available", "warning")
        elif action == "copy_url":
            copy_to_clipboard(v.user.html_url)
            self.flash = FlashMessage("copied", "success")

    def _open_item(self, v):
        if v.kind in ("search", "trending", "user_repos"):
            idx = v.box.selected
            if 0 <= idx < len(v.data):
                self.open_detail(v.data[idx])
        elif v.kind == "bookmarks":
            b = v.data[v.box.selected] if v.box.selected < len(v.data) else None
            if b:
                self.load_repo_by_name(*b["full_name"].split("/", 1))
        elif v.kind == "history":
            q = v.data[v.box.selected] if v.box.selected < len(v.data) else None
            if q:
                self.open_search(q)

    def _clone_current(self, v):
        if isinstance(v, ListView) and v.box.multi:
            repos = [v.data[i] for i in sorted(v.box.multi) if i < len(v.data)]
            if repos and self.modal.confirm("Clone %d repos?" % len(repos)):
                ok = 0
                for r in repos:
                    code, _ = self.clone.clone(r)
                    if code == 0:
                        ok += 1
                self.flash = FlashMessage("cloned %d/%d" % (ok, len(repos)), "success")
            return
        if isinstance(v, DetailView):
            self.clone_repo(v.repo)
            return
        idx = v.box.selected
        if isinstance(v, ListView) and 0 <= idx < len(v.data) \
                and isinstance(v.data[idx], Repo):
            self.clone_repo(v.data[idx])

    def _toggle_bookmark(self, v):
        repo = None
        if isinstance(v, DetailView):
            repo = v.repo
        elif isinstance(v, ListView) and 0 <= v.box.selected < len(v.data):
            repo = v.data[v.box.selected] if isinstance(v.data[v.box.selected], Repo) else None
        if repo:
            added = self.bookmarks.toggle(repo.full_name, repo.stargazers_count)
            self.flash = FlashMessage(
                "bookmarked %s" % repo.full_name if added else "removed bookmark", "success")

    def _browser_current(self, v):
        if isinstance(v, ListView) and 0 <= v.box.selected < len(v.data):
            repo = v.data[v.box.selected]
            if isinstance(repo, Repo) and repo.html_url:
                if not open_browser(repo.html_url):
                    self.flash = FlashMessage("no browser available", "warning")

    def _copy_current(self, v):
        url = ""
        if isinstance(v, DetailView):
            url = v.repo.html_url
        elif isinstance(v, ListView) and 0 <= v.box.selected < len(v.data):
            d = v.data[v.box.selected]
            url = d.html_url if isinstance(d, Repo) else (
                d.get("html_url", "") if isinstance(d, dict) else "")
        if url and copy_to_clipboard(url):
            self.flash = FlashMessage("copied URL", "success")
        else:
            self.flash = FlashMessage("clipboard tool unavailable", "warning")

    def _search_prompt(self):
        q = self.modal.input_prompt("Search GitHub", hint="query (Esc cancels)")
        if q:
            self.open_search(q)

    def _filter_prompt(self, v):
        def on_tab(buf):
            if ":" not in buf:
                cands = complete_filter_key(buf)
                if len(cands) == 1:
                    return cands[0] + ":"
                if cands:
                    self.flash = FlashMessage("keys: " + " ".join(cands), "info", 1.5)
                    return buf
            return buf

        text = self.modal.input_prompt(
            "Filters (key:value ...)",
            hint="e.g. language:python stars:>500 · trending: since:weekly lang:go · Tab=keys", on_tab=on_tab)
        if text is None or not text.strip():
            return
        filters = {}
        for part in text.split():
            if ":" in part:
                k, val = part.split(":", 1)
                filters[k.strip()] = val.strip()
        if v.kind == "search":
            v.filters = filters
            v.page = 1
            self.load_view(v)
        elif v.kind == "trending":
            opts = {}
            for k, val in filters.items():
                if k == "since":
                    opts["since"] = val
                elif k == "lang":
                    opts["language"] = val
                elif k == "spoken":
                    opts["spoken"] = val
            v.trending_opts = opts
            self.load_view(v)
        msg = "filters: %s" % " ".join(filters.values()) if filters else "filters cleared"
        self.flash = FlashMessage(msg, "info")

    # ---------- rendering ----------

    def _render_progress(self, pct):
        self._render_once(status="cloning %d%%" % pct, progress=pct)

    def _render_once(self, status=None, progress=None):
        try:
            self._render(status, progress)
            self.stdscr.refresh()
        except curses.error:
            pass

    def _render(self, status=None, progress=None):
        std = self.stdscr
        std.erase()
        lay = self.layout
        rows, cols = std.getmaxyx()
        if lay.rows != rows or lay.cols != cols:
            lay.update()

        # header
        h_rect = lay.header
        title = " GitHub Scraper TUI "
        lay.text(h_rect, 0, 0, title, colors.PAIR_HEADER, curses.A_BOLD)
        crumbs = truncate(self.breadcrumb(), max(0, cols - 60))
        if lay.header[2] >= 3:
            lay.text(h_rect, 1, 2, crumbs, colors.PAIR_CYAN)
            rl = self.client.rate.label()
            right = ""
            if self.cfg.show_clock:
                clock = time.strftime("%H:%M:%S")
                reset = self.client.rate.seconds_to_reset()
                reset_s = "  resets in %dm" % (reset // 60) if reset else ""
                right = "%s  %s" % (clock, rl + reset_s)
            else:
                right = rl
            lay.text(h_rect, 0, max(0, cols - len(right) - 2), right,
                     colors.PAIR_RED if self.client.rate.low() else colors.PAIR_GREEN)
        else:
            right = time.strftime("%H:%M") if self.cfg.show_clock else ""
            lay.text(h_rect, 0, max(0, cols - len(right) - 1), right, colors.PAIR_GREEN)
            lay.text(h_rect, 0, max(0, cols - len(right) - 40), truncate(crumbs, 30), colors.PAIR_GREEN)
        if self.offline:
            lay.text(h_rect, 0, max(0, cols - 32), "⚠ OFFLINE — cached data", colors.PAIR_ERR)

        # sidebar
        if lay.sidebar:
            lay.border(lay.sidebar, "rounded", title="Menu")
            y, x, h, w = lay.sidebar
            for i, (key, label) in enumerate(MENU):
                pair = colors.PAIR_GREEN
                lay.text(lay.sidebar, 1 + i, 2, "%-12s %s" % (label, "[" + key + "]"), pair)
            bcount = len(self.bookmarks.list_collection())
            lay.text(lay.sidebar, h - 2, 2, "Bookmarks: %d  Queue: %d" % (
                bcount, len(self.clone.queue)), colors.PAIR_YELLOW)
        else:
            lay.border(lay.main, "rounded", active=True)

        # main panel
        v = self.view
        inner = lay.border(lay.main, "rounded", active=True, title=v.title if v else "")
        if isinstance(v, ListView):
            self._render_list(v, inner)
        elif isinstance(v, DetailView):
            self._render_detail(v, inner)
        elif isinstance(v, UserView):
            self._render_user(v, inner)
        else:
            lay.text(lay.main, 1, 2, "no view", colors.PAIR_YELLOW)

        # status bar
        s_rect = lay.status
        hints = self._hints(v)
        st = status or (self.flash.msg if self.flash and self.flash.live else "")
        if st:
            pair = self.flash.pair() if self.flash else colors.PAIR_CYAN
            lay.text(s_rect, 0, 1, truncate(st, cols - 2), pair)
        spinner_ch = self.spinner.frame()
        right = "%s  %d items" % (spinner_ch, len(v.box.rows) if v else 0)
        lay.text(s_rect, 0, max(0, cols - len(right) - 1), right, colors.PAIR_MAGENTA)
        if s_rect[2] >= 2:
            lay.text(s_rect, 1, 1, truncate(hints, cols - 2), colors.PAIR_MAGENTA)
        if progress is not None:
            render_progress(std, s_rect[0], 1, min(30, cols - 2), progress / 100.0)
        std.move(0, 0)

    def _render_list(self, v, inner):
        y, x, h, w = inner
        v.box.render(self.stdscr, y, x, h, w, focused=True,
                     row_pair=lambda i, sel, foc: None)

    def _render_detail(self, v, inner):
        y, x, h, w = inner
        if v.error:
            self.stdscr.addstr(y, x, truncate("✖ " + v.error, w), curses.color_pair(colors.PAIR_ERR))
            return
        tab_line = " ".join(
            ("[%s]" if i == v.tab else " %s ") % t for i, t in enumerate(DETAIL_TABS))
        self.stdscr.addstr(y, x, truncate(tab_line, w),
                           curses.color_pair(colors.PAIR_SELECTED if v.tab == 0 else colors.PAIR_CYAN))
        v.box.render(self.stdscr, y + 1, x, h - 1, w, focused=True,
                     row_pair=lambda i, sel, foc: v.pairs[i] if i < len(v.pairs) else None)

    def _render_user(self, v, inner):
        y, x, h, w = inner
        u = v.user
        lines = [
            "(%s) %s  %s" % (u.login[:1].upper() if u.login else "?", u.login, u.name),
            "─" * min(w - 2, 40),
        ]
        if isinstance(u, User):
            lines += [
                "Bio: %s" % (u.bio or "-"),
                "Location: %s  Company: %s" % (u.location or "-", u.company or "-"),
                "Email: %s  Blog: %s" % (u.email or "-", u.blog or "-"),
                "Repos: %d  Followers: %d  Following: %d" % (
                    u.public_repos, u.followers, u.following),
                "Member since: %s" % format_date(u.created_at),
                "",
                "Enter: list repos   o: open profile",
            ]
        else:
            lines += [
                "Description: %s" % (u.description or "-"),
                "Repos: %d" % u.public_repos,
                "Created: %s" % format_date(u.created_at),
                "",
                "Enter: list repos   o: open profile",
            ]
        for i, line in enumerate(lines):
            if i >= h:
                break
            pair = colors.PAIR_CYAN if i == 0 else colors.PAIR_GREEN
            self.stdscr.addstr(y + i, x, truncate(line, w), curses.color_pair(pair))

    def _hints(self, v):
        if isinstance(v, DetailView):
            return "Tab sections · ↑/↓ scroll · Enter open · c clone · b bookmark · o browser · " \
                   "y copy · q back"
        if isinstance(v, UserView):
            return "Enter repos · o profile · q back"
        if v.kind == "history":
            return "Enter run search · / filter · d delete · x clear all"
        return "↑/↓ move · Enter open · c clone · b bookmark · Space select · / search · q back"

    # ---------- event loop ----------

    def run(self):
        self.open_trending()
        self.stdscr.timeout(200)
        self.stdscr.keypad(1)
        self._rl_warned = False
        while not self.done:
            self._render_once()
            if not self.view:
                break
            if self.client.rate.low() and not self._rl_warned:
                self.flash = FlashMessage("rate limit low — automatic paging paused", "warning")
                self._rl_warned = True
            elif not self.client.rate.low():
                self._rl_warned = False
            try:
                key = self.stdscr.getch()
            except KeyboardInterrupt:
                self.done = True
                break
            if key == -1:
                continue
            self.on_key(key)
        return 0

    def on_key(self, key):
        if key == curses.KEY_RESIZE:
            self.layout.update()
            return
        if key == curses.KEY_MOUSE:
            try:
                _, mx, my, _, bstate = curses.getmouse()
            except Exception:
                return
            v = self.view
            wheel_down = getattr(curses, "BUTTON5_PRESSED", 1 << 21)
            if bstate & (curses.BUTTON4_PRESSED | wheel_down):
                if isinstance(v, ListView):
                    act = "page_up" if bstate & curses.BUTTON4_PRESSED else "page_down"
                    self._list_action(v, act)
                elif isinstance(v, DetailView):
                    act = "page_up" if bstate & curses.BUTTON4_PRESSED else "page_down"
                    self._detail_action(v, act)
            elif bstate & curses.BUTTON1_CLICKED:
                if isinstance(v, ListView):
                    idx = v.box.top + (my - self.layout.main[0] - 1)
                    if 0 <= idx < len(v.box.rows):
                        v.box.selected = idx
                        v.box.clamp(self.layout.main[2] - 2)
            return
        v = self.view
        section = "list"
        if isinstance(v, DetailView):
            section = "detail"
        action = self.keys.resolve(section, key) or self.keys.resolve("global", key)
        if action:
            self.handle(action)


class UserView:
    def __init__(self, app, user, is_org=False):
        self.app = app
        self.user = user
        self.is_org = is_org
        self.title = "User: %s" % user.login

    def reload(self):
        try:
            ep = (endpoints.org if self.is_org else endpoints.user)(self.user.login)
            d = self.app.client.get(ep, ttl=600, force=True)
            self.user = Org.from_dict(d) if self.is_org else User.from_dict(d)
        except GitHubError as e:
            self.app.flash = FlashMessage(err_text(e), "error")
