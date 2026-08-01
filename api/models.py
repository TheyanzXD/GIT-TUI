# api/models.py - Typed data classes for API responses.

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List


def _d(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    if isinstance(data, dict):
        return data.get(key, default)
    return default


@dataclass
class Repo:
    full_name: str
    name: str = ""
    owner: str = ""
    description: str = ""
    html_url: str = ""
    clone_url: str = ""
    ssh_url: str = ""
    homepage: str = ""
    language: str = ""
    license: str = ""
    default_branch: str = "main"
    stargazers_count: int = 0
    forks_count: int = 0
    watchers_count: int = 0
    open_issues_count: int = 0
    created_at: str = ""
    pushed_at: str = ""
    updated_at: str = ""
    archived: bool = False
    topics: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Repo":
        lic = _d(d, "license") or {}
        return cls(
            full_name=_d(d, "full_name", ""),
            name=_d(d, "name", ""),
            owner=_d(_d(d, "owner", {}) or {}, "login", ""),
            description=_d(d, "description") or "",
            html_url=_d(d, "html_url", ""),
            clone_url=_d(d, "clone_url", ""),
            ssh_url=_d(d, "ssh_url", ""),
            homepage=_d(d, "homepage") or "",
            language=_d(d, "language") or "",
            license=_d(lic, "spdx_id", "") or "",
            default_branch=_d(d, "default_branch", "main"),
            stargazers_count=int(_d(d, "stargazers_count", 0) or 0),
            forks_count=int(_d(d, "forks_count", 0) or 0),
            watchers_count=int(_d(d, "watchers_count", 0) or 0),
            open_issues_count=int(_d(d, "open_issues_count", 0) or 0),
            created_at=_d(d, "created_at", "") or "",
            pushed_at=_d(d, "pushed_at", "") or "",
            updated_at=_d(d, "updated_at", "") or "",
            archived=bool(_d(d, "archived", False)),
            topics=list(_d(d, "topics", []) or []),
        )


@dataclass
class User:
    login: str
    name: str = ""
    bio: str = ""
    location: str = ""
    email: str = ""
    blog: str = ""
    company: str = ""
    html_url: str = ""
    avatar_url: str = ""
    public_repos: int = 0
    followers: int = 0
    following: int = 0
    created_at: str = ""

    @classmethod
    def from_dict(cls, d):
        return cls(
            login=_d(d, "login", ""),
            name=_d(d, "name") or "",
            bio=_d(d, "bio") or "",
            location=_d(d, "location") or "",
            email=_d(d, "email") or "",
            blog=_d(d, "blog") or "",
            company=_d(d, "company") or "",
            html_url=_d(d, "html_url", ""),
            avatar_url=_d(d, "avatar_url", ""),
            public_repos=int(_d(d, "public_repos", 0) or 0),
            followers=int(_d(d, "followers", 0) or 0),
            following=int(_d(d, "following", 0) or 0),
            created_at=_d(d, "created_at", "") or "",
        )


@dataclass
class Org:
    login: str
    name: str = ""
    description: str = ""
    html_url: str = ""
    public_repos: int = 0
    created_at: str = ""
    avatar_url: str = ""

    @classmethod
    def from_dict(cls, d):
        return cls(
            login=_d(d, "login", ""),
            name=_d(d, "name") or "",
            description=_d(d, "description") or "",
            html_url=_d(d, "html_url", ""),
            public_repos=int(_d(d, "public_repos", 0) or 0),
            created_at=_d(d, "created_at", "") or "",
            avatar_url=_d(d, "avatar_url", ""),
        )


@dataclass
class Commit:
    sha: str = ""
    author: str = ""
    date: str = ""
    message: str = ""
    html_url: str = ""

    @classmethod
    def from_dict(cls, d):
        commit = _d(d, "commit", {}) or {}
        author = _d(commit, "author", {}) or {}
        return cls(
            sha=_d(d, "sha", "")[:7],
            author=_d(_d(commit, "author", {}) or {}, "name", "-"),
            date=_d(author, "date", ""),
            message=(_d(commit, "message", "") or "").splitlines()[0] if _d(commit, "message") else "",
            html_url=_d(d, "html_url", ""),
        )


@dataclass
class Issue:
    number: int = 0
    title: str = ""
    labels: List[str] = field(default_factory=list)
    author: str = ""
    created_at: str = ""
    html_url: str = ""
    state: str = "open"

    @classmethod
    def from_dict(cls, d):
        return cls(
            number=int(_d(d, "number", 0) or 0),
            title=_d(d, "title", ""),
            labels=[lab.get("name", "") for lab in (_d(d, "labels", []) or [])],
            author=_d(_d(d, "user", {}) or {}, "login", "-"),
            created_at=_d(d, "created_at", ""),
            html_url=_d(d, "html_url", ""),
            state=_d(d, "state", "open"),
        )


@dataclass
class Release:
    tag_name: str = ""
    name: str = ""
    published_at: str = ""
    body: str = ""
    html_url: str = ""
    assets: int = 0

    @classmethod
    def from_dict(cls, d):
        return cls(
            tag_name=_d(d, "tag_name", ""),
            name=_d(d, "name") or "",
            published_at=_d(d, "published_at", ""),
            body=(_d(d, "body") or "")[:120],
            html_url=_d(d, "html_url", ""),
            assets=len(_d(d, "assets", []) or []),
        )


@dataclass
class Contributor:
    login: str = ""
    contributions: int = 0

    @classmethod
    def from_dict(cls, d):
        return cls(
            login=_d(d, "login", ""),
            contributions=int(_d(d, "contributions", 0) or 0),
        )


@dataclass
class TreeEntry:
    path: str = ""
    type: str = "blob"
    size: int = 0

    @classmethod
    def from_dict(cls, d):
        return cls(
            path=_d(d, "path", ""),
            type=_d(d, "type", "blob"),
            size=int(_d(d, "size", 0) or 0),
        )


def json_or_none(text):
    try:
        return json.loads(text)
    except ValueError:
        return None
