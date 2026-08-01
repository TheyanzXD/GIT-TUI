# api/endpoints.py - GitHub API endpoint URL builders.

from urllib.parse import quote

GITHUB_API_BASE = "https://api.github.com"
GITHUB_WEB = "https://github.com"


def search_repos(query, sort="stars", order="desc", page=1, per_page=30):
    return "%s/search/repositories?q=%s&sort=%s&order=%s&page=%d&per_page=%d" % (
        GITHUB_API_BASE, quote(query), sort, order, page, per_page)


def repo(owner, name):
    return "%s/repos/%s/%s" % (GITHUB_API_BASE, owner, name)


def readme(owner, name, ref=None):
    url = "%s/repos/%s/%s/readme" % (GITHUB_API_BASE, owner, name)
    return url + ("?ref=" + ref if ref else "")


def tree(owner, name, branch="HEAD", recursive=True):
    return "%s/repos/%s/%s/git/trees/%s%s" % (
        GITHUB_API_BASE, owner, name, branch, "?recursive=1" if recursive else "")


def commits(owner, name, page=1, per_page=30, path=None):
    url = "%s/repos/%s/%s/commits?page=%d&per_page=%d" % (
        GITHUB_API_BASE, owner, name, page, per_page)
    if path:
        url += "&path=%s" % quote(path)
    return url


def issues(owner, name, page=1, per_page=30, labels=None, state="open"):
    url = "%s/repos/%s/%s/issues?state=%s&page=%d&per_page=%d" % (
        GITHUB_API_BASE, owner, name, state, page, per_page)
    if labels:
        url += "&labels=%s" % quote(labels)
    return url


def releases(owner, name, page=1, per_page=30):
    return "%s/repos/%s/%s/releases?page=%d&per_page=%d" % (
        GITHUB_API_BASE, owner, name, page, per_page)


def contributors(owner, name, per_page=10):
    return "%s/repos/%s/%s/contributors?per_page=%d" % (
        GITHUB_API_BASE, owner, name, per_page)


def languages(owner, name):
    return "%s/repos/%s/%s/languages" % (GITHUB_API_BASE, owner, name)


def user(username):
    return "%s/users/%s" % (GITHUB_API_BASE, username)


def user_repos(username, page=1, per_page=30, sort="updated", order="desc"):
    return "%s/users/%s/repos?sort=%s&order=%s&page=%d&per_page=%d" % (
        GITHUB_API_BASE, username, sort, order, page, per_page)


def org(orgname):
    return "%s/orgs/%s" % (GITHUB_API_BASE, orgname)


def org_repos(orgname, page=1, per_page=30, sort="updated", order="desc"):
    return "%s/orgs/%s/repos?sort=%s&order=%s&page=%d&per_page=%d" % (
        GITHUB_API_BASE, orgname, sort, order, page, per_page)


def rate_limit():
    return "%s/rate_limit" % GITHUB_API_BASE


def trending(since="daily", language=None, spoken=None):
    url = "%s/trending" % GITHUB_WEB
    parts = []
    if language:
        url += "/" + quote(language)
    if since != "daily":
        parts.append("since=" + since)
    if spoken:
        parts.append("spoken_language_code=" + quote(spoken))
    if parts:
        url += "?" + "&".join(parts)
    return url


def web_repo(owner, name):
    return "%s/%s/%s" % (GITHUB_WEB, owner, name)


def web_release(owner, name, tag):
    return "%s/%s/%s/releases/tag/%s" % (GITHUB_WEB, owner, name, quote(tag))
