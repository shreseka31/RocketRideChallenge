# GitHub Issue Snapshot Connector

A reusable Python connector that imports one page of open issues from a public
GitHub repository into a local SQLite file, then reads the saved issues offline.
Pull requests are excluded. Importing an issue again updates its title and URL
without creating a duplicate.

## Prerequisites and dependencies

- Python 3.10 or newer with SQLite support (verified here on Python 3.12).
- Internet access for imports. Reads and automated tests work offline.
- No third-party dependencies, API token, paid tools, or hosted services.
- Git is needed only to publish the project with the Git commands below.

The project uses Python's standard library: `urllib`, `sqlite3`, `json`,
`argparse`, and `unittest`. No `pip install` command is needed.

## Local setup and run

Download or clone this repository, then open a terminal in the project folder.
On macOS/Linux:

```bash
python3 --version
python3 -m unittest discover -s tests -v
python3 connector.py import pallets/itsdangerous --db issues.db
python3 connector.py read pallets/itsdangerous --db issues.db
python3 connector.py import pallets/itsdangerous --db issues.db
python3 connector.py import invalid-repository --db issues.db
```

On Windows, replace `python3` with `py -3`. The final command intentionally
returns an error and exits with status 1. Successful commands exit with status 0.
Each command starts a new process, so the read demonstrates persistence after
the import process exits. To verify offline behavior manually, disconnect from
the internet after a successful import and run the read command again.

`--db` can be any writable SQLite file path, including an absolute path. It
defaults to `issues.db` in the current working directory. The parent directory
must already exist. Use the same path for import and read. Database files are
ignored by Git. An empty path or `:memory:` is rejected because this connector
requires persistent file storage.

## Example inputs and outputs

The examples below are illustrative; live titles and counts change.

```bash
python3 connector.py import example/project --db issues.db
```

```json
{
  "ok": true,
  "repository": "example/project",
  "count": 1,
  "imported_count": 1,
  "issues": [
    {
      "repository": "example/project",
      "number": 1,
      "title": "Fix login",
      "url": "https://github.com/example/project/issues/1"
    }
  ],
  "error": null
}
```

```bash
python3 connector.py read example/project --db issues.db
```

Read returns the same result fields and saved records, with `imported_count`
set to `null`. Reading a repository with no saved issues succeeds with
`count: 0` and `issues: []`. Reading a new database initializes an empty table.

```bash
python3 connector.py import invalid-repository --db issues.db
```

```json
{
  "ok": false,
  "repository": "invalid-repository",
  "count": 0,
  "imported_count": null,
  "issues": [],
  "error": {
    "code": "invalid_repository",
    "message": "Use owner/name, for example pallets/flask, rather than a URL."
  }
}
```

## Reusable functions

```python
from connector import import_issues, read_issues

imported = import_issues("pallets/itsdangerous", db_path="issues.db")
saved = read_issues("pallets/itsdangerous", db_path="issues.db")
if not imported["ok"]:
    print(imported["error"]["message"])
```

Both functions return ordinary dictionaries and lists that can be serialized
with `json.dumps`. Their top-level keys are always `ok`, `repository`, `count`,
`imported_count`, `issues`, and `error`. Issue objects always contain
`repository`, `number`, `title`, and `url`. `count` is the number of saved issues
returned. `imported_count` is the number of issue records in this API page,
excluding pull requests; it is `null` for reads and failures. An error result
contains no issue records, but does not imply that previously saved data was
deleted. Expected failures have codes `invalid_repository`, `api_error`,
`invalid_response`, or `database_error`.

## Automated tests

```bash
python3 -m unittest discover -s tests -v
```

The 24 tests use mocked HTTP responses and temporary database files. They cover
import and offline read, pull request exclusion, updates without duplicates,
repository isolation and case normalization, persistence in a new process,
HTTP/API failures, invalid inputs and malformed JSON, database failures,
transaction rollback, and JSON results and CLI exit codes. No network call or
permanent database is needed for tests. A mixed issues/pull requests fixture
checks filtering; the repeated-import test checks both row count and updated
title/URL. The restart test launches a separate Python process.

## Live demo

```bash
python3 demo.py pallets/itsdangerous --db demo.db --pause
```

This helper performs real imports, reads in a separate process, repeats the
import, checks the database for duplicates, and shows an invalid repository
error. It displays at most two issue records per step to keep a recording
readable; the connector itself returns all locally saved records. Run it once
before recording. If the repository has no open issues, choose another public
repository with open issues, such as `pallets/flask`.

Public imports can fail because of network restrictions or GitHub rate limits.
The helper stops if an import or read fails; it never substitutes mock data.
See [DEMO_GUIDE.md](DEMO_GUIDE.md) for the recording script and submission steps.

## Scope and limitations

- Fetches only page 1, with `state=open` and `per_page=100`. This may contain
  fewer than 100 actual issues because GitHub includes pull requests.
- Saves imported records cumulatively. A later import does not remove an issue
  that closed or moved off the first page. Removing absent records would be
  unreliable when only one page is fetched. This is a local snapshot store,
  not a complete synchronization of currently open issues.
- Repository input is trimmed and normalized to lowercase. Repository renames
  are not reconciled with earlier saved names.
- Uses unauthenticated public API access and a 15-second request timeout.
  There are no retries, pagination, private-repository support, or UI.

## AI and other tools used

- **ChatGPT / Codex coding agent:** read the assessment, researched the API,
  generated and reviewed Python code and tests, and drafted the architecture
  and demo instructions. Review the code and adapt these explanations to your
  understanding before submitting.
- **Web search and official GitHub/Python documentation:** verified the issues
  endpoint's pull request behavior, page parameters, and SQLite connection and
  transaction handling.
- **Terminal and Python 3.12:** ran the automated tests and attempted the live
  demo successfully. The live run imported three issues from
  `pallets/itsdangerous`, read them in a new process, and repeated the import
  with zero duplicates. Run it locally again for your own recording.
- **Python `unittest` and `unittest.mock`:** exercised success and failure
  paths deterministically without depending on GitHub availability.
- **Python `sqlite3`:** implemented storage and checked uniqueness.

One integration detail addressed with AI assistance was that GitHub's issues
endpoint returns pull requests alongside issues. The implementation excludes
records containing `pull_request`, following GitHub's documentation. This was
verified with a mocked response containing two issues and one pull request;
only the two issues are stored. AI-assisted design also selected a composite
primary key and UPSERT; tests verified that a second import changes existing
titles and URLs while leaving the row count unchanged. Mock tests verify these
behaviors; they do not replace the real API call required in the demo.

## References

- [GitHub REST API: repository issues](https://docs.github.com/en/rest/issues/issues#list-repository-issues)
- [Python sqlite3 documentation](https://docs.python.org/3/library/sqlite3.html)
- [SQLite UPSERT](https://www.sqlite.org/lang_UPSERT.html)

## Project files

- `connector.py`: reusable functions and CLI.
- `tests/test_connector.py`: automated tests.
- `Architecture.MD`: interface, data flow, schema, and tradeoffs.
- `demo.py`: live recording helper.
- `DEMO_GUIDE.md`: two-minute recording plan and submission checklist.
- `LEARNING_GUIDE.md`: explanation of the code and practice questions.
