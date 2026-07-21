# GitHub Scraper TUI

A fast, lightweight, and beautiful Terminal User Interface (TUI) for browsing, searching, and managing GitHub repositories directly from your terminal. Built with Python and `curses`.

## Features

- **Trending Repositories:** Instantly view trending projects created in the last 30 days.
- **Advanced Search:** Search for specific repositories or users with intuitive filters.
- **Interactive Details:** View repository metadata (Author, Stars, Forks, Language, Created Date) in a clean, scrollable card interface.
- **Seamless Cloning:** Clone any repository directly from the interface using a single key press.
- **Dynamic UI:** Automatic resizing support for different terminal sizes and layouts.
- **Pagination:** Smooth lazy-loading of repository lists.

## Requirements

- Python 3.x
- Standard library modules only (no external pip dependencies required beyond base Python).

## Getting Started

1. **Clone the repository:**
   ```bash
   git clone <url-to-this-repo>
   cd TUI
   ```

2. **Run the application:**
   ```bash
   python3 main.py
   ```

## Controls

| Key | Action |
| :--- | :--- |
| **▲ / ▼** | Navigate through the repository list |
| **ENTER** | Show detailed information about the selected repository |
| **C** | Clone the selected repository |
| **N** | Load the next page of repositories |
| **S** | Open search menu (Repository or User) |
| **T** | Refresh / View trending repositories |
| **Q** | Quit application |

## Project Structure

- `main.py`: Application entry point and TUI loop.
- `ui.py`: UI rendering engine using `curses`.
- `api.py`: GitHub API interaction layer.
- `config.py`: Configuration constants and color theme management.

## Contributing

Contributions are welcome! Please feel free to open issues or submit pull requests for new features, bug fixes, or UI improvements.

## Developer

- **Developed by:** [TheyanzXD](https://github.com/TheyanzXD)
