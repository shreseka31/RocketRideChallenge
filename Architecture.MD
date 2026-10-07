# Architecture (used AI to help Generate but thoroughly reviewed all content)

## Interface

`import_issues(repository, db_path="issues.db")` fetches and saves one page of
issues. `read_issues(repository, db_path="issues.db")` returns saved records
using only SQLite. Both return JSON-compatible dictionaries with the same keys:
`ok`, `repository`, `count`, `imported_count`, `issues`, and `error`.
`count` is the number of records returned from storage; `imported_count` is the
number of issues in this import, or `null` for reads/failures. Each issue has
`repository`, `number`, `title`, and `url`. Expected errors return `ok: false`
and an error object with `code` and `message`.

The CLI in `connector.py` exposes these functions as `import` and `read`, prints
JSON, and uses exit codes 0 for success and 1 for connector failure. Argument
parser usage errors use exit code 2. `demo.py` is a separate demonstration
helper that calls the CLI in new processes and summarizes its output.

## Components and data flow

All runtime code is in one small module. `_repository` validates owner/name
input and normalizes case. `_fetch` makes one unauthenticated HTTPS request:
`GET /repos/{owner}/{name}/issues?state=open&per_page=100&page=1`. It uses an
explicit User-Agent, GitHub JSON Accept header, API version header, and
15-second timeout. It excludes objects with a `pull_request` key and maps
`html_url` to the stored `url`.

Import validates the entire API response before opening storage, executes
parameterized UPSERTs in one transaction, reads the saved rows, then commits
and closes the connection. A failed write rolls back the batch. Read validates
the repository, opens storage, initializes the table if needed, selects rows
for that repository ordered by issue number, and closes the connection. It
does not call `_fetch` or any network function. SQLite persists on disk, so
subsequent processes can read the same file.

## Database schema

```sql
CREATE TABLE issues (
    repository TEXT NOT NULL,
    number INTEGER NOT NULL CHECK (number > 0),
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    PRIMARY KEY (repository, number)
);
```

Issue numbers are unique within a repository, so the composite primary key
prevents duplicates without colliding across repositories. `ON CONFLICT
(repository, number) DO UPDATE` replaces the saved title and URL. Parameterized
queries store titles as plain data, including quotes and SQL-like text.

## Configuration and error handling

The database file path is passed directly to either function or through CLI
`--db`. It defaults to `issues.db`, relative to the working directory. Parent
directories must exist, and `:memory:` is rejected to preserve restart behavior.
The SQLite lock timeout is five seconds. No credentials are required or stored.

Validation failures return `invalid_repository`. HTTP errors (including a
useful 404 explanation), network errors, and timeouts return `api_error`.
Invalid JSON or issue fields return `invalid_response`. SQLite/path failures
return `database_error`. API failures cannot change saved data because fetching
comes first. SQL write failures roll back. Connections are explicitly closed
with `contextlib.closing`; the connection's own context manager manages
transactions, rather than closing the connection.

## Tradeoffs and verification

Python's standard library avoids dependency installation and keeps the code
easy to inspect. SQLite gives persistent local storage and transactional
UPSERTs without a server. Only one page is fetched, as required. Earlier records
are retained when absent from a later page, because absence does not prove an
issue closed. This means reads are accumulated local snapshots, not a live list
of every currently open issue. No pagination, retry policy, authentication,
repository rename reconciliation, schema migrations, or UI is included.

Automated tests mock HTTP but use real temporary SQLite files. They check
filtering, updates and uniqueness, offline reads, restart persistence,
repository isolation, malformed responses, API/database failures, and rollback
of a batch rejected by a database trigger. The recording helper uses actual
GitHub requests and checks stored row counts against unique issue numbers.
