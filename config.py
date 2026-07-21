# config.py

import curses

ITEMS_PER_PAGE = 10
GITHUB_API_BASE = "https://api.github.com"
HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "Termux-TUI-Scraper-Python"
}

def setup_colors():
    """ Safely sets up color pairs to remain compatible across all Termux/curses versions """
    try:
        curses.start_color()
    except Exception:
        pass
    
    try:
        curses.use_default_colors()
    except Exception:
        pass
        
    if curses.has_colors():
        # Setup modern cohesive terminal color scheme
        try:
            # Pair 1: Green text, default background (Success, secondary lines)
            curses.init_pair(1, curses.COLOR_GREEN, -1)
            # Pair 2: Selected cursor highlight (White text on Cyan bg, or black on green/cyan)
            curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)
            # Pair 3: Cyan text, default background (Primary frames, titles)
            curses.init_pair(3, curses.COLOR_CYAN, -1)
            # Pair 4: Yellow text, default background (Infos, labels, warning)
            curses.init_pair(4, curses.COLOR_YELLOW, -1)
            # Pair 5: Red text, default background (Error alerts)
            curses.init_pair(5, curses.COLOR_RED, -1)
            # Pair 6: Magenta text, default background (Instructions, keys)
            curses.init_pair(6, curses.COLOR_MAGENTA, -1)
        except Exception:
            # Fallback to standard color allocations if default colors fails on ultra-old setups
            try:
                curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
                curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_GREEN)
                curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)
                curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
                curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK)
                curses.init_pair(6, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
            except Exception:
                pass
