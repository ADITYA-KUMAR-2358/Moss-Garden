"""GitHub REST helpers.

Endpoints used here are the documented OAuth and REST v3 routes:
https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps
https://docs.github.com/en/rest
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

_REPO_NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_API = "https://api.github.com"
_OAUTH_AUTHORIZE = "https://github.com/login/oauth/authorize"
_OAUTH_TOKEN = "https://github.com/login/oauth/access_token"


class GitHubError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class GitHubRateLimit(GitHubError):
    pass


@dataclass(frozen=True)
class CommitCandidate:
    sha: str
    message: str
    committed_at: datetime


@dataclass(frozen=True)
class RepoCandidate:
    github_repo_id: int
    full_name: str
    private: bool


def authorize_url(*, client_id: str, redirect_uri: str, scopes: str, state: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    if scopes:
        params["scope"] = scopes
    return f"{_OAUTH_AUTHORIZE}?{urlencode(params)}"


def parse_next_link(header: str | None) -> str | None:
    if not header:
        return None
    for part in header.split(","):
        if 'rel="next"' in part:
            return part.split(";", 1)[0].strip().strip("<>")
    return None


def validate_full_name(full_name: str) -> str:
    if not _REPO_NAME.fullmatch(full_name):
        raise GitHubError("Repository name is not valid")
    return full_name


def eligible_commit(item: dict, login: str) -> CommitCandidate | None:
    parents = item.get("parents") or []
    if len(parents) > 1:
        return None
    author = item.get("author") or {}
    if author.get("login") != login:
        return None
    sha = str(item.get("sha") or "")
    commit = item.get("commit") or {}
    message = str((commit.get("message") or ""))[:2000]
    authored = (commit.get("author") or {}).get("date")
    if not sha or not authored:
        return None
    moment = datetime.fromisoformat(str(authored).replace("Z", "+00:00"))
    return CommitCandidate(sha=sha, message=message, committed_at=moment)


def _open(request: Request, timeout: int = 20):
    return urlopen(request, timeout=timeout)


def _read(response) -> tuple[int, dict | list, str | None]:
    status = getattr(response, "status", 200)
    header = response.headers.get("Link") if getattr(response, "headers", None) else None
    raw = response.read().decode()
    payload = json.loads(raw) if raw else {}
    return status, payload, header


class GitHubClient:
    def __init__(self, token: str, opener=_open):
        self.token = token
        self.opener = opener

    def _request(self, url: str, method: str = "GET", body: dict | None = None):
        data = None if body is None else json.dumps(body).encode()
        request = Request(
            url,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "moss-garden",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
            },
        )
        try:
            with self.opener(request) as response:
                return _read(response)
        except HTTPError as error:
            if error.code in (403, 429):
                raise GitHubRateLimit("GitHub rate limit reached", error.code) from error
            detail = error.read().decode(errors="replace")[:200]
            raise GitHubError(detail or "GitHub request failed", error.code) from error

    def current_login(self) -> str:
        _status, payload, _link = self._request(f"{_API}/user")
        if not isinstance(payload, dict) or not payload.get("login"):
            raise GitHubError("GitHub user response was missing a login")
        return str(payload["login"])

    def list_repos(self) -> list[RepoCandidate]:
        found: dict[int, RepoCandidate] = {}
        for item in self._collect_repos(f"{_API}/user/repos?per_page=100&sort=pushed"):
            found[item.github_repo_id] = item
        for item in self._installation_repos():
            found.setdefault(item.github_repo_id, item)
        return list(found.values())

    def _collect_repos(self, url: str, key: str | None = None) -> list[RepoCandidate]:
        found: list[RepoCandidate] = []
        while url:
            _status, payload, link = self._request(url)
            rows = payload.get(key) if key and isinstance(payload, dict) else payload
            if not isinstance(rows, list):
                break
            for item in rows:
                full_name = str(item.get("full_name") or "")
                if not _REPO_NAME.fullmatch(full_name) or "id" not in item:
                    continue
                found.append(
                    RepoCandidate(
                        github_repo_id=int(item["id"]),
                        full_name=full_name,
                        private=bool(item.get("private")),
                    )
                )
            url = parse_next_link(link)
        return found

    def _installation_repos(self) -> list[RepoCandidate]:
        try:
            _status, payload, _link = self._request(f"{_API}/user/installations")
        except GitHubError:
            return []
        installations = payload.get("installations") if isinstance(payload, dict) else None
        if not isinstance(installations, list):
            return []
        found: list[RepoCandidate] = []
        for installation in installations:
            install_id = installation.get("id") if isinstance(installation, dict) else None
            if not install_id:
                continue
            try:
                found.extend(
                    self._collect_repos(
                        f"{_API}/user/installations/{install_id}/repositories?per_page=100",
                        key="repositories",
                    )
                )
            except GitHubError:
                continue
        return found

    def iter_commits(self, full_name: str, login: str, since: str):
        safe = validate_full_name(full_name)
        url = (
            f"{_API}/repos/{safe}/commits?author={quote(login)}"
            f"&since={quote(since)}&per_page=100"
        )
        while url:
            _status, payload, link = self._request(url)
            if not isinstance(payload, list):
                break
            page = []
            for item in payload:
                candidate = eligible_commit(item, login)
                if candidate is not None:
                    page.append(candidate)
            yield page
            url = parse_next_link(link)


def exchange_code(
    *,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
    opener=_open,
) -> str:
    body = json.dumps(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }
    ).encode()
    request = Request(
        _OAUTH_TOKEN,
        data=body,
        method="POST",
        headers={"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "moss-garden"},
    )
    try:
        with opener(request) as response:
            payload = json.loads(response.read().decode())
    except HTTPError as error:
        raise GitHubError("GitHub token exchange failed", error.code) from error
    token = payload.get("access_token") if isinstance(payload, dict) else None
    if not token:
        raise GitHubError("GitHub did not return an access token")
    return str(token)


def convert_app_manifest(code: str, opener=_open) -> dict:
    """Turn a GitHub App manifest code into client credentials. The code is single use."""
    request = Request(
        f"{_API}/app-manifests/{quote(code, safe='')}/conversions",
        data=b"{}",
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "moss-garden",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with opener(request) as response:
            payload = json.loads(response.read().decode())
    except HTTPError as error:
        raise GitHubError("GitHub could not finish creating the app", error.code) from error
    if not isinstance(payload, dict) or not payload.get("client_id") or not payload.get("client_secret"):
        raise GitHubError("GitHub did not return app credentials")
    return payload
