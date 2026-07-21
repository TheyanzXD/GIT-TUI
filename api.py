# api.py

import json
import urllib.request
from urllib.error import HTTPError, URLError
from config import GITHUB_API_BASE, HEADERS

def _make_request(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        # Added a 10s timeout to prevent hanging on slow internet
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except HTTPError as e:
        if e.code == 403:
            return {"error": "API Limit Habis / Terblokir"}
        elif e.code == 404:
            return {"error": "Tidak Ditemukan (404)"}
        return {"error": f"HTTP Error {e.code}"}
    except URLError:
        return {"error": "Offline / Gagal Koneksi"}
    except Exception as e:
        return {"error": str(e)}

def fetch_trending_repos(query, page=1, per_page=10):
    url = f"{GITHUB_API_BASE}/search/repositories?q={query}&sort=stars&order=desc&page={page}&per_page={per_page}"
    return _make_request(url)

def fetch_user_repos(username, page=1, per_page=10):
    url = f"{GITHUB_API_BASE}/users/{username}/repos?sort=updated&page={page}&per_page={per_page}"
    return _make_request(url)

def check_rate_limit():
    url = f"{GITHUB_API_BASE}/rate_limit"
    return _make_request(url)
