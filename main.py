# main.py - Entry point: CLI commands and TUI bootstrap.

import argparse
import csv
import json
import sys

import curses

from api import endpoints
from api.client import GitHubClient, GitHubError
from api.models import Repo, User, Org
from config import Config
from utils import setup_logging


def _client(cfg):
    return GitHubClient(cfg)


def _emit(items, args, headers):
    if getattr(args, "json", False):
        print(json.dumps(items, indent=2, default=str))
    elif getattr(args, "csv", False):
        w = csv.writer(sys.stdout)
        w.writerow(headers)
        for row in items:
            w.writerow([row.get(h) for h in headers])
    else:
        for row in items:
            print("  ".join(str(row.get(h, "")) for h in headers))


def _repo_dicts(repos):
    return [{
        "full_name": r.full_name,
        "description": r.description,
        "stars": r.stargazers_count,
        "forks": r.forks_count,
        "language": r.language,
        "html_url": r.html_url,
    } for r in repos]


def cmd_search(args, cfg):
    client = _client(cfg)
    qualifiers = []
    for flag, key in (("lang", "language"), ("stars", "stars"), ("forks", "forks")):
        val = getattr(args, flag, None)
        if val:
            qualifiers.append("%s:%s" % (key, val))
    q = " ".join([args.query] + qualifiers)
    url = endpoints.search_repos(q, sort=args.sort, order=args.order, page=args.page,
                                 per_page=cfg.per_page)
    data = client.get(url, ttl=300, force=args.refresh)
    repos = [Repo.from_dict(d) for d in data.get("items", [])]
    _emit(_repo_dicts(repos), args, ["full_name", "stars", "forks", "language", "html_url"])
    return 0


def cmd_view(args, cfg):
    client = _client(cfg)
    d = client.get(endpoints.repo(args.owner, args.repo), ttl=600, force=args.refresh)
    r = Repo.from_dict(d)
    _emit([{
        "full_name": r.full_name, "description": r.description, "homepage": r.homepage,
        "language": r.language, "license": r.license, "default_branch": r.default_branch,
        "stars": r.stargazers_count, "forks": r.forks_count,
        "watchers": r.watchers_count, "open_issues": r.open_issues_count,
        "created_at": r.created_at, "pushed_at": r.pushed_at,
        "topics": r.topics, "html_url": r.html_url,
    }], args, ["full_name", "stars", "forks", "language", "html_url"])
    return 0


def cmd_user(args, cfg):
    client = _client(cfg)
    try:
        d = client.get(endpoints.user(args.username), ttl=600, force=args.refresh)
        u = User.from_dict(d)
        d_out = {"login": u.login, "name": u.name, "bio": u.bio, "location": u.location,
                 "email": u.email, "blog": u.blog, "company": u.company,
                 "public_repos": u.public_repos, "followers": u.followers,
                 "following": u.following, "created_at": u.created_at, "html_url": u.html_url}
    except GitHubError:
        d = client.get(endpoints.org(args.username), ttl=600, force=args.refresh)
        o = Org.from_dict(d)
        d_out = {"login": o.login, "name": o.name, "description": o.description,
                 "public_repos": o.public_repos, "created_at": o.created_at,
                 "html_url": o.html_url}
    _emit([d_out], args, ["login", "name", "public_repos", "html_url"])
    return 0


def cmd_trending(args, cfg):
    client = _client(cfg)
    from features.trending import fetch_trending
    raw = fetch_trending(client, since=args.period, language=args.lang, spoken=args.spoken)
    _emit([{
        "full_name": r["full_name"], "description": r["description"], "stars": r["stars"],
        "forks": r["forks"], "language": r["language"], "stars_today": r["today"],
        "html_url": r["html_url"],
    } for r in raw], args, ["full_name", "stars", "forks", "language", "html_url"])
    return 0


def cmd_clone(args, cfg):
    from features.clone import CloneManager
    client = _client(cfg)
    d = client.get(endpoints.repo(args.owner, args.repo), ttl=600)
    repo = Repo.from_dict(d)
    manager = CloneManager(cfg)
    protocol = "ssh" if args.ssh else cfg.clone_protocol
    code, target = manager.clone(repo, dest_dir=args.dir, protocol=protocol)
    print("OK: %s" % target if code == 0 else "FAILED: %s" % repo.full_name)
    return 0 if code == 0 else 1


def cmd_bookmarks(args, cfg):
    from features.bookmarks import BookmarkManager
    manager = BookmarkManager()
    if args.export:
        path = manager.export_markdown(args.export)
        print("exported → %s" % path)
        return 0
    if args.import_file:
        count = manager.import_json(args.import_file)
        print("imported %d bookmarks" % count)
        return 0
    items = [{"full_name": b["full_name"], "stars": b["stars"]} for b in manager.list_collection()]
    _emit(items, args, ["full_name", "stars"])
    return 0


def cmd_config(args, cfg):
    if args.list:
        for k, v in sorted(cfg.data.items()):
            print("%s = %s" % (k, v))
    for kv in args.set or []:
        if "=" not in kv:
            print("invalid: %s (expected key=value)" % kv, file=sys.stderr)
            continue
        k, v = kv.split("=", 1)
        try:
            cfg.set(k, v)
            print("set %s = %s" % (k, v))
        except KeyError as e:
            print("error: %s" % e, file=sys.stderr)
    return 0


def _parser():
    p = argparse.ArgumentParser(
        prog="github-tui",
        description="GitHub Scraper TUI - browse, search, and manage GitHub repos from the terminal")
    common = argparse.ArgumentParser(add_help=False)
    for name, help_ in (("--debug", "enable debug logging"),
                        ("--no-tui", "do not launch the TUI"),
                        ("--json", "output results as JSON"),
                        ("--csv", "output results as CSV"),
                        ("--refresh", "bypass cache")):
        common.add_argument(name, action="store_true", help=help_)
    p.add_argument("--debug", action="store_true", help="enable debug logging")
    p.add_argument("--no-tui", action="store_true", help="do not launch the TUI")
    p.add_argument("--json", action="store_true", help="output results as JSON")
    p.add_argument("--csv", action="store_true", help="output results as CSV")
    p.add_argument("--refresh", action="store_true", help="bypass cache")
    sub = p.add_subparsers(dest="command")

    s = sub.add_parser("search", help="search repositories", parents=[common])
    s.add_argument("query")
    s.add_argument("--lang")
    s.add_argument("--stars")
    s.add_argument("--forks")
    s.add_argument("--sort", choices=["stars", "forks", "updated", "name"], default="stars")
    s.add_argument("--order", choices=["desc", "asc"], default="desc")
    s.add_argument("--page", type=int, default=1)

    v = sub.add_parser("view", help="show repository details", parents=[common])
    v.add_argument("owner_repo", metavar="OWNER/REPO")

    u = sub.add_parser("user", help="show user or org profile", parents=[common])
    u.add_argument("username")

    t = sub.add_parser("trending", help="fetch trending repositories", parents=[common])
    t.add_argument("--lang")
    t.add_argument("--period", choices=["daily", "weekly", "monthly"], default="daily")
    t.add_argument("--spoken")

    c = sub.add_parser("clone", help="clone a repository", parents=[common])
    c.add_argument("owner_repo", metavar="OWNER/REPO")
    c.add_argument("--dir")
    c.add_argument("--ssh", action="store_true")

    b = sub.add_parser("bookmarks", help="manage bookmarks", parents=[common])
    b.add_argument("--export", metavar="FILE")
    b.add_argument("--import", dest="import_file", metavar="FILE")

    cfgp = sub.add_parser("config", help="view or set configuration", parents=[common])
    cfgp.add_argument("--set", action="append", metavar="KEY=VALUE")
    cfgp.add_argument("--list", action="store_true")
    return p


def _resolve_view_args(args):
    spec = getattr(args, "owner_repo", None) or ""
    if spec:
        parts = spec.strip().strip("/").split("/")
        if len(parts) == 2:
            return parts
    return None


def main(argv=None):
    parser = _parser()
    args = parser.parse_args(argv)
    setup_logging(args.debug)
    cfg = Config.load()

    if args.command == "config":
        return cmd_config(args, cfg)

    if args.command is None:
        if args.no_tui:
            parser.print_help()
            return 0
        try:
            return curses.wrapper(lambda stdscr: _run_tui(stdscr, cfg))
        except Exception as e:
            print("[!] TUI error: %s" % e, file=sys.stderr)
            if args.debug:
                raise
            return 1

    try:
        if args.command == "search":
            return cmd_search(args, cfg)
        if args.command == "view":
            parts = _resolve_view_args(args)
            if not parts:
                print("error: expected OWNER/REPO", file=sys.stderr)
                return 1
            args.owner, args.repo = parts
            return cmd_view(args, cfg)
        if args.command == "user":
            return cmd_user(args, cfg)
        if args.command == "trending":
            return cmd_trending(args, cfg)
        if args.command == "clone":
            parts = _resolve_view_args(args)
            if not parts:
                print("error: expected OWNER/REPO", file=sys.stderr)
                return 1
            args.owner, args.repo = parts
            return cmd_clone(args, cfg)
        if args.command == "bookmarks":
            return cmd_bookmarks(args, cfg)
    except GitHubError as e:
        print("[!] %s" % e.message, file=sys.stderr)
        return 1
    return 0


def _run_tui(stdscr, cfg):
    from app import App
    return App(stdscr, cfg).run()


if __name__ == "__main__":
    sys.exit(main())
