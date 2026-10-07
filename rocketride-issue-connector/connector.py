"""Import one page of public GitHub issues and read saved issues offline."""

import argparse
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_DB = "issues.db"
SCHEMA = """
CREATE TABLE IF NOT EXISTS issues (
    repository TEXT NOT NULL,
    number INTEGER NOT NULL CHECK (number > 0),
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    PRIMARY KEY (repository, number)
)
"""
UPSERT = """
INSERT INTO issues (repository, number, title, url) VALUES (?, ?, ?, ?)
ON CONFLICT(repository, number) DO UPDATE SET
    title = excluded.title,
    url = excluded.url
"""


class ConnectorError(Exception):
    """An expected failure that can be returned as a JSON-compatible result."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _result(repository, issues=None, imported_count=None, error=None):
    issues = [] if issues is None else issues
    return {
        "ok": error is None,
        "repository": repository,
        "count": len(issues),
        "imported_count": imported_count,
        "issues": issues,
        "error": error,
    }


def _repository(value):
    if not isinstance(value, str):
        raise ConnectorError("invalid_repository", "Repository must be a string in owner/name format.")
    value = value.strip()
    parts = value.split("/")
    if len(parts) != 2:
        raise ConnectorError("invalid_repository", "Use owner/name, for example pallets/flask, rather than a URL.")
    owner, name = parts
    valid_owner = re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", owner)
    valid_name = re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", name)
    if not valid_owner or not valid_name or name in {".", ".."}:
        raise ConnectorError("invalid_repository", "Repository must contain a valid owner and repository name.")
    return value.lower()


def _fetch(repository):
    # GitHub's issues endpoint also returns pull requests. Filter them below.
    request = Request(
        f"https://api.github.com/repos/{repository}/issues?state=open&per_page=100&page=1",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "rocketride-issue-connector",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.load(response)
    except HTTPError as exc:
        if exc.code == 404:
            message = "Repository not found or not publicly accessible (HTTP 404). Check owner/name."
        elif exc.code in {403, 429}:
            message = f"GitHub rejected the request (HTTP {exc.code}); access restrictions or rate limits may apply. Try later."
        else:
            message = f"GitHub API request failed (HTTP {exc.code}). Try again later."
        raise ConnectorError("api_error", message) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise ConnectorError("api_error", "Could not reach GitHub. Check your internet connection and try again.") from exc
    except (ValueError, UnicodeError) as exc:
        raise ConnectorError("invalid_response", "GitHub did not return valid JSON.") from exc

    if not isinstance(payload, list):
        raise ConnectorError("invalid_response", "Expected a list of issues from GitHub.")
    issues = []
    for item in payload:
        if not isinstance(item, dict):
            raise ConnectorError("invalid_response", "GitHub returned an invalid issue record.")
        if "pull_request" in item:
            continue
        number, title, url = item.get("number"), item.get("title"), item.get("html_url")
        if (type(number) is not int or number <= 0 or not isinstance(title, str)
                or not isinstance(url, str) or not url):
            raise ConnectorError("invalid_response", "An issue is missing a valid number, title, or URL.")
        issues.append({"repository": repository, "number": number, "title": title, "url": url})
    return issues


def _connect(db_path):
    if not isinstance(db_path, (str, Path)) or not str(db_path).strip() or str(db_path) == ":memory:":
        raise ConnectorError("database_error", "Choose a nonempty file path for persistent SQLite storage.")
    return sqlite3.connect(str(db_path), timeout=5)


def _saved(connection, repository):
    rows = connection.execute(
        "SELECT repository, number, title, url FROM issues WHERE repository = ? ORDER BY number",
        (repository,),
    ).fetchall()
    return [dict(zip(("repository", "number", "title", "url"), row)) for row in rows]


def _failure(repository, exc):
    if isinstance(exc, ConnectorError):
        code, message = exc.code, str(exc)
    else:
        code, message = "database_error", f"Could not use the SQLite database: {exc}"
    return _result(repository, error={"code": code, "message": message})


def import_issues(repository, db_path=DEFAULT_DB):
    """Fetch one page, upsert its issues, and return all locally saved issues.

    This accumulates imported records; it does not delete issues missing from a
    later page. Expected API, validation, and database failures return ok=False.
    """
    name = repository if isinstance(repository, str) else None
    try:
        name = _repository(repository)
        issues = _fetch(name)  # Validate the whole response before changing storage.
        with closing(_connect(db_path)) as connection:
            with connection:  # Commit on success; roll back on failure.
                connection.execute(SCHEMA)
                connection.executemany(
                    UPSERT,
                    [(name, i["number"], i["title"], i["url"]) for i in issues],
                )
                saved = _saved(connection, name)
        return _result(name, saved, imported_count=len(issues))
    except (ConnectorError, sqlite3.Error, ValueError) as exc:
        return _failure(name, exc)


def read_issues(repository, db_path=DEFAULT_DB):
    """Return saved issues using only SQLite, including in a fresh process."""
    name = repository if isinstance(repository, str) else None
    try:
        name = _repository(repository)
        with closing(_connect(db_path)) as connection:
            with connection:
                connection.execute(SCHEMA)
                saved = _saved(connection, name)
        return _result(name, saved)
    except (ConnectorError, sqlite3.Error, ValueError) as exc:
        return _failure(name, exc)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("import", "read"))
    parser.add_argument("repository", help="Public repository as owner/name")
    parser.add_argument("--db", default=DEFAULT_DB, help="SQLite file path (default: issues.db)")
    args = parser.parse_args(argv)
    function = import_issues if args.command == "import" else read_issues
    result = function(args.repository, args.db)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
