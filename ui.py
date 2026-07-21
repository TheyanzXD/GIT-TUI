# ui.py

import curses
from config import setup_colors

def wrap_text(text, max_width):
    """ Helper to wrap text nicely inside a given width """
    if not text:
        return ["Tidak ada deskripsi."]
    wrapped_lines = []
    for paragraph in text.splitlines():
        if not paragraph:
            wrapped_lines.append("")
            continue
        words = paragraph.split(" ")
        curr_line = []
        curr_len = 0
        for word in words:
            # Handle long words/URLs that exceed max_width
            if len(word) > max_width:
                if curr_line:
                    wrapped_lines.append(" ".join(curr_line))
                    curr_line = []
                    curr_len = 0
                wrapped_lines.append(word[:max_width])
                word = word[max_width:]
                while len(word) > max_width:
                    wrapped_lines.append(word[:max_width])
                    word = word[max_width:]
                
            if curr_len + len(word) + (1 if curr_line else 0) > max_width:
                wrapped_lines.append(" ".join(curr_line))
                curr_line = [word]
                curr_len = len(word)
            else:
                curr_line.append(word)
                curr_len += len(word) + (1 if len(curr_line) > 1 else 0)
        if curr_line:
            wrapped_lines.append(" ".join(curr_line))
    return wrapped_lines


class TermuxUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        try:
            curses.curs_set(0)
        except Exception:
            pass
        setup_colors()
        self.height, self.width = stdscr.getmaxyx()
    
    def resize(self):
        """ Recalculates screen boundaries safely on resize events """
        try:
            curses.update_lines_cols()
        except Exception:
            pass
        self.height, self.width = self.stdscr.getmaxyx()
        self.stdscr.clear()
        self.stdscr.refresh()
    
    def draw_menu(self, title, items, selected_idx, viewport_top, rate_limit, status_msg=""):
        self.stdscr.clear()
        self.height, self.width = self.stdscr.getmaxyx()
        
        # 1. Screen size safety check
        if self.height < 14 or self.width < 45:
            self.stdscr.addstr(1, 2, "⚠️ LAYAR TERLALU KECIL", curses.color_pair(5) | curses.A_BOLD)
            self.stdscr.addstr(3, 2, f"Lebar minimum: 45 | Tinggi: 14", curses.color_pair(3))
            self.stdscr.addstr(4, 2, f"Layar Anda: {self.width}x{self.height}", curses.color_pair(3))
            self.stdscr.addstr(6, 2, "Silakan putar layar (rotate)", curses.color_pair(1))
            self.stdscr.addstr(7, 2, "atau perkecil ukuran font.", curses.color_pair(1))
            self.stdscr.refresh()
            return

        # 2. Draw ASCII Logo if screen width permits, otherwise draw clean text header
        logo_y = 1
        if self.width >= 55:
            # Beautiful double-line ASCII logo (centered)
            logo_lines = [
                "╔╦╗╔═╗╦═╗╔╦╗╦ ╦═╗ ╦  ╔═╗╔═╗╦═╗╔═╗╔═╗╔═╗╦═╗",
                " ║ ║╣ ╠╦╝║║║║ ║╔╩╦╝  ╚═╗║  ╠╦╝╠═╣╠═╝║╣ ╠╦╝",
                " ╩ ╚═╝╩╚═╩ ╩╚═╝╩ ╚═  ╚═╝╚═╝╩╚═╩ ╩╩  ╚═╝╩╚═"
            ]
            for i, line in enumerate(logo_lines):
                x_pos = (self.width - len(line)) // 2
                self.stdscr.addstr(logo_y + i, x_pos, line, curses.color_pair(3) | curses.A_BOLD)
            y_offset = logo_y + 3
        else:
            header_text = "●─── GITHUB SCRAPER TUI v2.0 ───●"
            x_pos = (self.width - len(header_text)) // 2
            self.stdscr.addstr(logo_y, x_pos, header_text, curses.color_pair(3) | curses.A_BOLD)
            y_offset = logo_y + 1

        # Divider line
        self.stdscr.addstr(y_offset, 2, "─" * (self.width - 4), curses.color_pair(1))
        y_offset += 1

        # 3. Mode, Stats & API rate limit
        mode_text = f" Mode: {title}"[:self.width // 2 - 2]
        api_text = f"API Limit: {rate_limit} "
        total_text = f"Total: {len(items)} Repos "
        
        stats_line = f"{mode_text:<{self.width // 2}}{total_text:>{self.width // 2 - len(api_text)}}{api_text}"
        self.stdscr.addstr(y_offset, 2, stats_line[:self.width - 4], curses.color_pair(4) | curses.A_BOLD)
        y_offset += 1
        
        # Divider line before main panel
        self.stdscr.addstr(y_offset, 2, "─" * (self.width - 4), curses.color_pair(1))
        y_offset += 1

        # 4. Main Repository List Panel (framed in a box)
        footer_height = 6 # We use 6 lines for our beautiful instructions box
        status_height = 2 if status_msg else 0
        list_start_y = y_offset
        list_end_y = self.height - footer_height - status_height - 1
        list_max_height = max(1, list_end_y - list_start_y - 1)
        
        # Draw Box around items
        # Top line
        self.stdscr.addstr(list_start_y, 2, "┌" + "─" * (self.width - 6) + "┐", curses.color_pair(1))
        # Label/Title on Top Line of Box
        self.stdscr.addstr(list_start_y, 4, "─┤ DAFTAR REPOSITORI ├─", curses.color_pair(1) | curses.A_BOLD)
        
        # Side borders & bottom line of box
        for y in range(list_start_y + 1, list_end_y):
            self.stdscr.addstr(y, 2, "│", curses.color_pair(1))
            self.stdscr.addstr(y, self.width - 3, "│", curses.color_pair(1))
        self.stdscr.addstr(list_end_y, 2, "└" + "─" * (self.width - 6) + "┘", curses.color_pair(1))
        
        # If there are items, draw pagination stats on the bottom of the box
        if items:
            cur_page_info = f" Halaman {selected_idx // 10 + 1} | Item {selected_idx + 1}/{len(items)} "
            self.stdscr.addstr(list_end_y, self.width - 6 - len(cur_page_info), cur_page_info, curses.color_pair(1) | curses.A_BOLD)

        # Draw List items inside the box
        for i in range(list_max_height):
            idx = viewport_top + i
            if idx >= len(items):
                # Clean rest of box
                y = list_start_y + 1 + i
                self.stdscr.addstr(y, 3, " " * (self.width - 6))
                continue
            
            y = list_start_y + 1 + i
            
            # Prefix selection indicator
            if idx == selected_idx:
                indicator = " ▶ "
                item_text = items[idx]
                # Full line highlighting
                display_text = f"{indicator}{item_text}"[:self.width - 6].ljust(self.width - 6)
                self.stdscr.addstr(y, 3, display_text, curses.color_pair(2) | curses.A_BOLD)
            else:
                indicator = "   "
                item_text = items[idx]
                display_text = f"{indicator}{item_text}"[:self.width - 6].ljust(self.width - 6)
                self.stdscr.addstr(y, 3, display_text, curses.color_pair(1))

        # 5. Draw status/notifications bar
        if status_msg:
            status_y = self.height - footer_height - 2
            # Use color pair based on status character
            if "❌" in status_msg or "Error" in status_msg or "GAGAL" in status_msg:
                color = curses.color_pair(5) # Red
            elif "✅" in status_msg or "BERHASIL" in status_msg:
                color = curses.color_pair(1) # Green/Success (Pair 1 is Green)
            else:
                color = curses.color_pair(4) # Yellow / Alert
                
            status_display = f" [INFO] {status_msg}"[:self.width-4].ljust(self.width-4)
            self.stdscr.addstr(status_y, 2, status_display, color | curses.A_BOLD)

        # 6. Beautiful instructions/legend panel (with nice custom double/single line box)
        footer_y = self.height - footer_height
        
        # Header border of controls box
        self.stdscr.addstr(footer_y, 2, "┌" + "─" * (self.width - 6) + "┐", curses.color_pair(3))
        self.stdscr.addstr(footer_y, 4, "─┤ PETUNJUK NAVIGASI & KONTROL ├─", curses.color_pair(3) | curses.A_BOLD)
        
        # Side borders
        for i in range(1, 5):
            self.stdscr.addstr(footer_y + i, 2, "│", curses.color_pair(3))
            self.stdscr.addstr(footer_y + i, self.width - 3, "│", curses.color_pair(3))
            # Fill inside
            self.stdscr.addstr(footer_y + i, 3, " " * (self.width - 6))
            
        # Bottom border
        self.stdscr.addstr(footer_y + 4, 2, "└" + "─" * (self.width - 6) + "┘", curses.color_pair(3))

        # Rows layout (dynamically truncating if screen is too narrow)
        row1 = " [▲/▼] Navigasi      │  [ENTER] Detail  │  [C] Clone Repositori"
        row2 = " [N] Muat Halaman    │  [S] Pencarian   │  [T] Trending GitHub"
        row3 = " [Q] Keluar"
        
        self.stdscr.addstr(footer_y + 1, 4, row1[:self.width-8], curses.color_pair(6) | curses.A_BOLD)
        self.stdscr.addstr(footer_y + 2, 4, row2[:self.width-8], curses.color_pair(6) | curses.A_BOLD)
        self.stdscr.addstr(footer_y + 3, 4, row3[:self.width-8], curses.color_pair(6) | curses.A_BOLD)

        self.stdscr.refresh()

    def get_input(self, prompt):
        """ Draws a beautiful centered input popup box and reads user input safely """
        try:
            curses.curs_set(1)
        except Exception:
            pass
        self.height, self.width = self.stdscr.getmaxyx()
        
        # Dimensions of input modal
        box_w = min(60, self.width - 6)
        box_h = 5
        
        start_x = (self.width - box_w) // 2
        start_y = (self.height - box_h) // 2
        
        input_str = []
        max_chars = box_w - len(prompt) - 6
        if max_chars < 5:
            max_chars = 15
            
        while True:
            # Draw Popup Box
            self.stdscr.addstr(start_y, start_x, "┌" + "─" * (box_w - 2) + "┐", curses.color_pair(3))
            self.stdscr.addstr(start_y + 1, start_x, "│" + " " * (box_w - 2) + "│", curses.color_pair(3))
            self.stdscr.addstr(start_y + 2, start_x, "│" + " " * (box_w - 2) + "│", curses.color_pair(3))
            self.stdscr.addstr(start_y + 3, start_x, "│" + " " * (box_w - 2) + "│", curses.color_pair(3))
            self.stdscr.addstr(start_y + 4, start_x, "└" + "─" * (box_w - 2) + "┘", curses.color_pair(3))
            
            # Draw Title of Input Box
            self.stdscr.addstr(start_y, start_x + 2, " 🔎 INPUT PENCARIAN ", curses.color_pair(3) | curses.A_BOLD)
            
            # Prompt
            self.stdscr.addstr(start_y + 2, start_x + 2, prompt[:box_w - 6], curses.color_pair(4) | curses.A_BOLD)
            
            # Current input value
            curr_val = "".join(input_str)
            input_start_x = start_x + 2 + len(prompt[:box_w - 6])
            
            # Draw content safely
            content_to_draw = curr_val[-max_chars:]
            self.stdscr.addstr(start_y + 2, input_start_x, content_to_draw, curses.color_pair(1))
            
            # Position cursor at the end of input
            cursor_x = min(start_x + box_w - 2, input_start_x + len(content_to_draw))
            self.stdscr.move(start_y + 2, cursor_x)
            self.stdscr.refresh()
            
            ch = self.stdscr.getch()
            if ch in [10, 13]: # Enter
                break
            elif ch in [27]: # ESC
                input_str = []
                break
            elif ch in [8, 127, curses.KEY_BACKSPACE]: # Backspace
                if len(input_str) > 0:
                    input_str.pop()
            elif 32 <= ch <= 126: # Normal printable characters
                if len(input_str) < 40: # Limit absolute length
                    input_str.append(chr(ch))
                    
        try:
            curses.curs_set(0)
        except Exception:
            pass
        return "".join(input_str).strip()
    
    def show_detail(self, title, info_dict, description):
        """ Shows a beautiful scrollable card with details of the repository """
        selected_scroll = 0
        while True:
            self.stdscr.clear()
            self.height, self.width = self.stdscr.getmaxyx()
            
            # Draw external box border for detail window
            box_w = min(76, self.width - 4)
            box_h = min(22, self.height - 2)
            
            if box_w < 35 or box_h < 10:
                # Fallback if screen is extremely small
                self.stdscr.addstr(1, 1, "⚠️ Layar Terlalu Kecil!", curses.color_pair(5) | curses.A_BOLD)
                self.stdscr.addstr(2, 1, "Lebarkan layar atau kurangi font.", curses.color_pair(4))
                self.stdscr.addstr(4, 1, "Tekan ESC atau ENTER untuk kembali...", curses.color_pair(3))
                self.stdscr.refresh()
                ch = self.stdscr.getch()
                if ch in [10, 13, 27]:
                    break
                continue
                
            start_x = (self.width - box_w) // 2
            start_y = (self.height - box_h) // 2
            
            # Draw custom border
            # Top border
            self.stdscr.addstr(start_y, start_x, "┌" + "─" * (box_w - 2) + "┐", curses.color_pair(3))
            # Bottom border
            self.stdscr.addstr(start_y + box_h - 1, start_x, "└" + "─" * (box_w - 2) + "┘", curses.color_pair(3))
            # Sides
            for y in range(start_y + 1, start_y + box_h - 1):
                self.stdscr.addstr(y, start_x, "│", curses.color_pair(3))
                self.stdscr.addstr(y, start_x + box_w - 1, "│", curses.color_pair(3))
                # Fill background of modal
                self.stdscr.addstr(y, start_x + 1, " " * (box_w - 2))
                
            # Title
            title_text = f" 📦 {title} "[:box_w - 6]
            self.stdscr.addstr(start_y, start_x + (box_w - len(title_text)) // 2, title_text, curses.color_pair(2) | curses.A_BOLD)
            
            # Render Info rows
            curr_y = start_y + 2
            for label, value in info_dict.items():
                if curr_y >= start_y + box_h - 2:
                    break
                # Label: Value
                lbl_str = f"  {label:8s} : "
                val_str = f"{value}"[:box_w - 18]
                self.stdscr.addstr(curr_y, start_x + 2, lbl_str, curses.color_pair(4) | curses.A_BOLD)
                self.stdscr.addstr(curr_y, start_x + 2 + len(lbl_str), val_str, curses.color_pair(1))
                curr_y += 1
                
            # Divider
            if curr_y < start_y + box_h - 2:
                self.stdscr.addstr(curr_y, start_x, "├" + "─" * (box_w - 2) + "┤", curses.color_pair(3))
                self.stdscr.addstr(curr_y, start_x + 4, " 📝 Deskripsi Repositori ", curses.color_pair(3) | curses.A_BOLD)
                curr_y += 1
                
            # Calculate description space
            desc_area_h = (start_y + box_h - 2) - curr_y
            if desc_area_h > 0:
                # Wrap description
                wrapped_desc = wrap_text(description or "Tidak ada deskripsi.", box_w - 6)
                
                # Draw scroll indicators if description overflows
                if len(wrapped_desc) > desc_area_h:
                    if selected_scroll > 0:
                        self.stdscr.addstr(curr_y - 1, start_x + box_w - 4, "▲", curses.color_pair(4) | curses.A_BOLD)
                    if selected_scroll + desc_area_h < len(wrapped_desc):
                        self.stdscr.addstr(start_y + box_h - 2, start_x + box_w - 4, "▼", curses.color_pair(4) | curses.A_BOLD)
                
                # Render wrapped lines
                for i in range(desc_area_h):
                    line_idx = selected_scroll + i
                    if line_idx >= len(wrapped_desc):
                        break
                    line_to_draw = wrapped_desc[line_idx]
                    self.stdscr.addstr(curr_y + i, start_x + 3, line_to_draw[:box_w - 6], curses.color_pair(1))
                    
            # Footer instructions
            footer_tips = " [▲/▼] Scroll Deskripsi | [ENTER/ESC] Kembali "
            self.stdscr.addstr(start_y + box_h - 1, start_x + (box_w - len(footer_tips)) // 2, footer_tips, curses.color_pair(2))
            
            self.stdscr.refresh()
            key = self.stdscr.getch()
            
            if key in [curses.KEY_UP, ord('w'), ord('W')]:
                if selected_scroll > 0:
                    selected_scroll -= 1
            elif key in [curses.KEY_DOWN, ord('s'), ord('S')]:
                if 'wrapped_desc' in locals() and selected_scroll + desc_area_h < len(wrapped_desc):
                    selected_scroll += 1
            elif key in [10, 13, 27]: # Enter or ESC
                break
