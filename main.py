# main.py

import curses
import datetime
import subprocess
from api import fetch_trending_repos, fetch_user_repos, check_rate_limit
from ui import TermuxUI
from config import ITEMS_PER_PAGE

def main(stdscr):
    # Initialize UI elements
    ui = TermuxUI(stdscr)
    
    last_month = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    trending_query = f"created:>{last_month}"
    
    current_mode = "TRENDING BULAN INI"
    current_query = trending_query
    search_type = "trending"
    
    page = 1
    selected_idx = 0
    viewport_top = 0
    status_msg = ""
    
    items = []
    raw_data = []

    def load_data(append=False):
        nonlocal items, raw_data, page
        rl = check_rate_limit()
        
        # Parse rate limit cleanly and safely
        if isinstance(rl, dict) and "resources" in rl:
            rem = rl.get("resources", {}).get("core", {}).get("remaining", "Habis")
        else:
            rem = "Offline/Error"
            
        error_occurred = None
        
        if search_type in ["trending", "repo"]:
            data = fetch_trending_repos(current_query, page=page, per_page=ITEMS_PER_PAGE)
            if isinstance(data, dict) and "items" in data:
                new_raw = data["items"]
                new_items = [f"{r.get('full_name', 'Unknown')} (⭐ {r.get('stargazers_count', 0)})" for r in new_raw]
                if not new_raw and page > 1:
                    error_occurred = "Semua data telah dimuat."
                elif not new_raw:
                    new_items = ["Repositori tidak ditemukan."]
            elif isinstance(data, dict) and "error" in data:
                new_raw = []
                error_occurred = data["error"]
                new_items = [f"Error: {error_occurred}"] if not append else []
            else:
                new_raw = []
                error_occurred = "Format data API tidak valid."
                new_items = [f"Error: {error_occurred}"] if not append else []
        else:
            data = fetch_user_repos(current_query, page=page, per_page=ITEMS_PER_PAGE)
            if isinstance(data, list):
                new_raw = data
                new_items = [f"{r.get('name', 'Unknown')} (⭐ {r.get('stargazers_count', 0)} | {r.get('language') or '-'})" for r in new_raw]
                if not new_raw and page > 1:
                    error_occurred = "Semua repositori user telah dimuat."
                elif not new_raw:
                    new_items = ["User tidak ditemukan atau Repositori kosong."]
            elif isinstance(data, dict) and "error" in data:
                new_raw = []
                error_occurred = data["error"]
                new_items = [f"Error: {error_occurred}"] if not append else []
            else:
                new_raw = []
                error_occurred = "User tidak ditemukan atau error koneksi."
                new_items = [f"Error: {error_occurred}"] if not append else []
                
        if append:
            if new_raw:
                raw_data.extend(new_raw)
                items.extend(new_items)
            else:
                # Revert page increase on failure or empty results
                if page > 1:
                    page -= 1
        else:
            raw_data = new_raw
            items = new_items
            
        return rem, error_occurred

    # Load initial data
    rate_info, err = load_data(append=False)
    if err:
        status_msg = f"{err}"

    while True:
        status_height = 2 if status_msg else 0
        footer_height = 6
        
        # Calculate maximum item list height dynamically based on terminal height
        list_max_height = max(1, ui.height - 6 - footer_height - status_height - 1)
        
        if selected_idx < viewport_top:
            viewport_top = selected_idx
        elif selected_idx >= viewport_top + list_max_height:
            viewport_top = selected_idx - list_max_height + 1
            
        ui.draw_menu(current_mode, items, selected_idx, viewport_top, rate_info, status_msg)
        key = stdscr.getch()
        
        if key == curses.KEY_RESIZE:
            ui.resize()
            status_msg = "🔄 Layar disesuaikan."
            continue
            
        elif key == curses.KEY_UP:
            status_msg = ""
            if selected_idx > 0:
                selected_idx -= 1
                
        elif key == curses.KEY_DOWN:
            status_msg = ""
            if selected_idx < len(items) - 1:
                selected_idx += 1
            else:
                # End of list loads next page automatically
                status_msg = "⏳ Mengambil data selanjutnya..."
                ui.draw_menu(current_mode, items, selected_idx, viewport_top, rate_info, status_msg)
                page += 1
                rate_info, err = load_data(append=True)
                if err:
                    status_msg = f"{err}"
                else:
                    status_msg = "✅ Data baru dimuat."
                if selected_idx < len(items) - 1:
                    selected_idx += 1
                    
        elif key in [10, 13]: # Enter to show detailed card
            if raw_data and selected_idx < len(raw_data):
                repo = raw_data[selected_idx]
                info = {
                    "Nama": repo.get('name', '-'),
                    "Author": repo.get('owner', {}).get('login', '-'),
                    "Bintang": f"⭐ {repo.get('stargazers_count', 0)}",
                    "Forks": f"🍴 {repo.get('forks_count', 0)}",
                    "Bahasa": repo.get('language', '-') or '-',
                    "Dibuat": repo.get('created_at', '')[:10] or '-',
                    "URL": repo.get('html_url', '-')
                }
                desc = repo.get('description') or "Tidak ada deskripsi."
                ui.show_detail(repo.get('full_name', 'Detail'), info, desc)
                status_msg = ""
                
        elif key in [ord('c'), ord('C')]: # Clone repo via git
            if raw_data and selected_idx < len(raw_data):
                repo = raw_data[selected_idx]
                clone_url = repo.get('clone_url')
                repo_name = repo.get('name')
                
                if not clone_url:
                    status_msg = "❌ URL clone tidak valid."
                    continue
                    
                status_msg = f"⚙️ MENG-CLONE: {repo_name}..."
                ui.draw_menu(current_mode, items, selected_idx, viewport_top, rate_info, status_msg)
                
                try:
                    result = subprocess.run(["git", "clone", clone_url], capture_output=True, text=True, check=False)
                    if result.returncode == 0:
                        status_msg = f"✅ CLONE BERHASIL: {repo_name} tersimpan."
                    else:
                        status_msg = "❌ CLONE GAGAL: Folder sudah ada atau koneksi putus."
                except Exception:
                    status_msg = "❌ KESALAHAN: Perintah git gagal dieksekusi (apakah git terinstall?)."
                    
        elif key in [ord('n'), ord('N')]: # Manual pagination load more
            status_msg = "⏳ Mengambil halaman selanjutnya..."
            ui.draw_menu(current_mode, items, selected_idx, viewport_top, rate_info, status_msg)
            page += 1
            rate_info, err = load_data(append=True)
            if err:
                status_msg = f"{err}"
            else:
                status_msg = "✅ Halaman baru dimuat."
            
        elif key in [ord('s'), ord('S')]: # Custom query searching
            status_msg = ""
            pilihan = ui.get_input("Cari [1] Repo / [2] User? (1/2): ")
            
            if pilihan == '1':
                query = ui.get_input("Kata kunci Repository: ")
                if query:
                    current_mode = f"CARI REPO: {query}"
                    current_query = query
                    search_type = "repo"
                    page = 1
                    selected_idx = 0
                    viewport_top = 0
                    status_msg = "⏳ Mencari Repository..."
                    ui.draw_menu(current_mode, items, selected_idx, viewport_top, rate_info, status_msg)
                    rate_info, err = load_data(append=False)
                    if err:
                        status_msg = f"❌ {err}"
                    else:
                        status_msg = "✅ Pencarian selesai."
                else:
                    status_msg = "⚠️ Pencarian dibatalkan."
                    
            elif pilihan == '2':
                query = ui.get_input("Username GitHub: ")
                if query:
                    current_mode = f"USER: {query}"
                    current_query = query
                    search_type = "user"
                    page = 1
                    selected_idx = 0
                    viewport_top = 0
                    status_msg = "⏳ Mencari User..."
                    ui.draw_menu(current_mode, items, selected_idx, viewport_top, rate_info, status_msg)
                    rate_info, err = load_data(append=False)
                    if err:
                        status_msg = f"❌ {err}"
                    else:
                        status_msg = "✅ Pencarian selesai."
                else:
                    status_msg = "⚠️ Pencarian dibatalkan."
            elif pilihan != "":
                status_msg = "❌ Pilihan tidak valid (harus 1 atau 2)."
                    
        elif key in [ord('t'), ord('T')]: # Reset/fetch monthly trending
            current_mode = "TRENDING BULAN INI"
            current_query = trending_query
            search_type = "trending"
            page = 1
            selected_idx = 0
            viewport_top = 0
            status_msg = "⏳ Memuat Trending..."
            ui.draw_menu(current_mode, items, selected_idx, viewport_top, rate_info, status_msg)
            rate_info, err = load_data(append=False)
            if err:
                status_msg = f"{err}"
            else:
                status_msg = "✅ Trending dimuat."
            
        elif key in [ord('q'), ord('Q')]: # Quit TUI cleanly
            break

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except Exception as e:
        print(f"\n[!] Terjadi kesalahan TUI: {e}\n")
