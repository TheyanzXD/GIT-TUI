# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-07-31

### Added
- Modular architecture: `api/`, `ui/`, `features/` packages with single-responsibility modules.
- Modern curses UI: 10-pair cohesive color scheme, 3 theme variants, rounded/bold/double Unicode borders with ASCII fallback.
- Panel layout system: header (breadcrumb, rate-limit, clock), sidebar (menu, counts), main panel, status bar; collapses gracefully on narrow (<80 cols) and short (<24 rows) terminals.
- Scrollable list widget with scrollbar, half-page paging (PgUp/PgDn), Home/End jumps, scroll-position memory per view, mouse wheel + click support.
- Repository detail view with 8 tabbed sections: Overview, README (markdown stripped to text with code blocks highlighted), File tree (expandable, per-file last commit), Commits, Issues (label filter), Releases, Contributors, Languages (bar chart).
- User & org profile view with repo listing.
- Advanced search with filter builder (tab-completed keys: language, stars, forks, created, pushed, topic, license, ...), sort cycling, order toggle.
- Search history (persistent, fuzzy recall, per-entry delete, clear).
- Bookmarks with named collections, markdown export, JSON import.
- Clone manager: protocol toggle, directory prompt, streaming progress, batch clone via multi-select, clone queue, editor hook.
- GitHub trending scraper (daily/weekly/monthly, language/spoken filters) with search-API fallback.
- Caching layer: in-memory LRU (200 entries, TTL) + on-disk JSON cache with per-category TTLs; `R` force-refresh, cache clear in settings.
- Error taxonomy with retries (3x, exponential backoff), rate-limit countdown, offline banner, debug log (`~/.github_tui/debug.log` via `--debug`).
- Config file `~/.github_tui/config.json` + CLI overrides; optional auth token (env `GITHUB_TOKEN` or config) for 5000 req/hr.
- Custom keybindings via `~/.github_tui/keybindings.json`.
- CLI commands: `search`, `view`, `user`, `trending`, `clone`, `bookmarks`, `config` with `--json` / `--csv` / `--no-tui`.
- Unit tests (unittest, 81 tests) including mocked curses screen and mocked HTTP client.
- Packaging: `pyproject.toml`, `github-tui` entry point; CI with lint / type-check / unit / integration / package jobs.

### Changed
- Entire app rewritten from the single-file v1 (Indonesian UI) to a modular v2 architecture; UI strings now English.

### Removed
- Legacy `ui.py` / `api.py` single-file modules.
