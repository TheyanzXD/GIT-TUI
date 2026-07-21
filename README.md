# 🚀 GitHub Scraper TUI

![Python](https://img.shields.io/badge/python-3.x-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
<!-- You can add a demo screenshot or GIF here -->
<!-- ![TUI Demo](./assets/demo.gif) -->

> A fast, lightweight, and beautiful Terminal User Interface (TUI) for browsing, searching, and managing GitHub repositories directly from your terminal. Built entirely with Python and `curses`.

---

## ✨ Features

*   🔥 **Trending Repositories:** Instantly view trending projects created in the last 30 days.
*   🔍 **Advanced Search:** Search for specific repositories or users with intuitive filters.
*   📋 **Interactive Details:** View repository metadata (Author, Stars, Forks, Language, Created Date) in a clean, scrollable card interface.
*   ⬇️ **Seamless Cloning:** Clone any repository directly from the interface using a single key press.
*   📐 **Dynamic UI:** Automatic resizing support for different terminal sizes and layouts.
*   📄 **Pagination:** Smooth lazy-loading of repository lists.

---

## 🛠️ Requirements

*   **Python 3.x**
*   *No external dependencies required!* Built purely using the standard library.

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone [https://github.com/TheyanzXD/GITSC-TUI.git](https://github.com/TheyanzXD/GITSC-TUI.git)
cd GITSC-TUI
```

### 2. Run the application
```bash
python main.py
```
### 3. Setup Quick Access (Recommended)
​You can create a permanent alias in your .bashrc to launch the TUI from anywhere in your terminal.
​Run the following command:
```bash
echo "alias tui='python ~/GITSC-TUI/main.py'" >> ~/.bashrc
source ~/.bashrc
```
Now, you can simply type tui in your terminal to open the application!

### 🎮 Controls
* ▲ / ▼ :  Navigate through the repository list
* ENTER  :   Show detailed information about the selected repository
* C      :   Clone the selected repository
* N      :   Load the next page of repositories
* S      :   Open search menu (Repository or User)
* T      :   Refresh / View trending repositories
* Q      :   Quit application

## 📁 Project Structure

```bash
GITSC_TUI/
├── main.py     # Application entry point and TUI loop
├── ui.py       # UI rendering engine using `curses`
├── api.py      # GitHub API interaction layer
└── config.py   # Configuration constants and color theme management
```
★★ 🤝 Contributing
​👨‍💻 Developer
​Developed by: github.com/TheyanzXD
