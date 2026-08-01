# 🚀 GitHub Scraper TUI

![Stars](https://img.shields.io/github/stars/Yanz-iyyo/GITSC-TUI.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Termux%20%7C%20WSL-lightgrey.svg)

> A fast, lightweight, and beautiful Terminal User Interface (TUI) for browsing, searching, and managing GitHub repositories directly from your terminal. Built entirely with Python and `curses` — **zero external dependencies**.

<!-- ![TUI Demo](./assets/demo.gif) -->

---

## ✨ Features

- **🔥 Trending**: scrape `github.com/trending` (daily/weekly/monthly, language & spoken-language filters) with automatic search-API fallback.
- **🔍 Advanced search**: full GitHub query syntax, filter builder with tab-completion, sort cycling, order toggle, persistent history with fuzzy recall.
- **📋 8-section detail view**: Overview, README (markdown→text, highlighted code blocks), expandable File Tree, Commits, Issues (label filter), Releases, Contributors, Languages bar chart.
- **👤 User & org profiles** with repo listing.
- **⬇️ Clone manager**: protocol toggle (HTTPS/SSH), directory prompt, streaming progress, batch clone, clone queue, editor hook.
- **🔖 Bookmarks**: named collections, markdown export, JSON import.
- **⚡ Caching**: in-memory LRU + on-disk cache with per-category TTLs; `R` force-refreshes, settings menu clears.
- **🎨 Modern UI**: 10-pair cohesive palette (3 themes), Unicode box-drawing borders with ASCII fallback, scrollbars, half-page paging, mouse wheel, flash messages, loading spinner, offline banner, rate-limit countdown.
- **📐 Responsive layout**: sidebar collapses < 80 cols, header collapses < 24 rows, full resize support.
- **⌨️ Custom keybindings** via `~/.github_tui/keybindings.json`.
- **🔌 CLI**: `search`, `view`, `user`, `trending`, `clone`, `bookmarks`, `config` with `--json` / `--csv` output for scripting.

---

## 🛠️ Installation

### pip / pipx

```bash
pip install github-tui
pipx install github-tui
github-tui
```

### Manual (or Termux / WSL)

```bash
git clone https://github.com/Yanz-iyyo/GITSC-TUI
cd GITSC-TUI
python main.py          # launch TUI
python main.py --help   # CLI
```

Quick-access alias:

```bash
echo "alias tui='python ~/GITSC-TUI/main.py'" >> ~/.bashrc
source ~/.bashrc
```

> **Termux note**: `curses` is bundled with Python on Termux — nothing to install.

---

## 🎮 Keybindings

| Key | Action |
|-----|--------|
| `q` / `Esc` | Go back / quit |
| `?` | Help modal |
| `:` | Command palette |
| `Ctrl+R` | Force refresh |
| `Tab` | Next detail section / switch focus |
| `↑/↓`, `j/k` | Move |
| `PgUp/PgDn` | Half page |
| `g`/`Home`, `G`/`End` | Top / bottom |
| `Enter` | Open item |
| `/` | Search input (history view: filter) |
| `f` | Filter builder |
| `s` / `O` | Cycle sort / toggle order |
| `h` | Search history |
| `b` / `B` | Toggle bookmark / bookmarks view |
| `c` / `n` | Clone / clone queue |
| `o` / `y` | Open in browser / copy URL |
| `Space` | Batch select |
| `d` / `D` | (history) delete / clear |
| `e` | Export list (CSV/MD) |
| `t` / `u` | Trending / user view |
| `x` | Settings (theme, cache, clock, mouse) |
| `Ctrl+R` / `Ctrl+C` | Force refresh / quit immediately |
| `Shift+Tab` | Previous detail section |

All keys are customizable: edit `~/.github_tui/keybindings.json` (generated on first run).

---

## ⚙️ Configuration

`~/.github_tui/config.json` (all keys overridable via CLI flags):

```json
{
  "token": "",              // GitHub PAT (or GITHUB_TOKEN env) → 5000 req/hr
  "default_sort": "stars",  // stars | forks | updated | name
  "default_order": "desc",  // desc | asc
  "clone_dir": "~/projects",
  "clone_protocol": "https",// https | ssh
  "editor": "",             // e.g. code, vim — opened after clone
  "color_theme": "default", // default | high_contrast | minimal
  "date_format": "relative",// relative | absolute
  "per_page": 30,
  "mouse_support": true,
  "unicode_borders": true,
  "show_clock": true,
  "cache_enabled": true
}
```

```bash
github-tui config --list
github-tui config --set per_page=20 clone_protocol=ssh
```

---

## 🔐 Authentication & rate limits

- **Unauthenticated**: 60 API requests/hour. The header bar shows live `API remaining/limit` plus a countdown to reset; at ≤10 remaining the display turns red, a warning flashes, and automatic page-loading pauses (manual navigation still works).
- **Authenticated**: 5000 requests/hour. Set a [Personal Access Token](https://github.com/settings/tokens) via config or env:

```bash
export GITHUB_TOKEN=ghp_...          # or:
github-tui config --set token=ghp_...
```

- Recommended scopes: `public_repo`, `read:user`, `read:org` (grants private-repo viewing if the token has access).
- On `429` / rate-limit exhaustion the UI shows the exact reset countdown instead of failing silently.
- **Trending view** scrapes `github.com/trending` directly (no API cost) and falls back to the search API when scraping is unavailable.

---

## 🔌 CLI usage

```bash
github-tui search flask --lang python --stars 1000 --sort stars --json
github-tui view pallets/flask
github-tui user torvalds --json
github-tui trending --period weekly --lang rust
github-tui clone pallets/flask --dir ~/code --ssh
github-tui bookmarks --export bookmarks.md
github-tui bookmarks --import backup.json
github-tui --debug   # debug logging → ~/.github_tui/debug.log
```

---

## 📁 Architecture

```
main.py            Entry point, argparse CLI, TUI bootstrap
app.py             Application controller & event loop (views, actions, rendering)
config.py          Config loading, defaults, persistence
utils.py           Shared helpers (truncate, format, markdown stripping, clipboard…)
api/
├── client.py      urllib wrapper: retries, error taxonomy, rate-limit state, cache
├── endpoints.py   API URL builders
├── cache.py       Memory LRU + disk cache (TTL)
└── models.py      Dataclasses (Repo, User, Issue, Commit, …)
ui/
├── colors.py      Color pairs & themes (8/256-color aware)
├── keys.py        Key binding registry + dispatcher
├── widgets.py     ListBox, Modal, Spinner, progress bar, flash messages
└── layout.py      Panel layout manager, borders, resize
features/
├── search.py      Query building, filter completion, history
├── bookmarks.py   Bookmark CRUD + collections + export/import
├── clone.py       Clone manager, queue, protocol selection
└── trending.py    Trending page scraper (HTMLParser) + API fallback
```

Cached data, config, history, and bookmarks live in `~/.github_tui/`.

---

## 🧭 Roadmap

- **v2.1** — mouse click support (already partial: wheel/click in lists), 256-color themes, plugin system (custom views)
- **v2.2** — GitHub Actions log viewer, PR/branch browser, diff viewer for commits
- **v2.3** — full offline mode (complete disk cache), HTML report export, multi-account support
- **v3.0** — async I/O (`asyncio`) for parallel API calls, optional `rich` backend alternative

---

## 🧪 Testing

```bash
python -m unittest discover -v     # 81 unit tests (stdlib unittest)
flake8 . --max-line-length=110
pylint -E app.py main.py api features ui config.py utils.py
mypy --strict --config-file pyproject.toml .
```

CI (GitHub Actions) runs lint, type-check, unit tests, integration tests (with a read-only token secret `READONLY_GITHUB_TOKEN`), and a package install check.

---

## 🤝 Contributing

1. Fork & clone the repo.
2. Keep it dependency-free; code must run on Python 3.8+ and degrade gracefully on limited terminals.
3. Add/update unit tests for changed logic.
4. Open a PR against `main`.

---

## 📜 Changelog

See [CHANGELOG.md](./CHANGELOG.md).

## License

MIT — © [TheyanzXD](https://github.com/TheyanzXD)
