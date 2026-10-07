# Understand and explain your connector

Start by running the project locally. Then read `connector.py` alongside this
guide. You should be able to explain and modify the code before submitting it.

## What the project does

`owner/name` identifies a repository, such as `pallets/itsdangerous`. Import
requests data from GitHub, filters and validates it, and saves it into a file.
Read loads that file and returns the saved records without contacting GitHub.

| Concept | Meaning in this project |
| --- | --- |
| API | GitHub's HTTPS endpoint that returns issue data as JSON. |
| JSON | A data format; Python dictionaries and lists can be converted to it. |
| Connector | Reusable code connecting an external API to local storage. |
| SQLite | A database stored in one local file; no database server is needed. |
| Primary key | The pair `(repository, number)` that uniquely identifies an issue. |
| UPSERT | Insert a new issue, or update its title and URL if its key already exists. |
| Transaction | A group of writes that commit together or roll back on failure. |
| Mock | A controlled stand-in for GitHub's HTTP response during tests. |

## Read the functions in this order

1. `main`: chooses import or read, passes the repository/database path, prints
   the result as JSON, and returns a success/failure exit status.
2. `import_issues`: the main workflow. Validate repository, fetch issues,
   open SQLite, run UPSERTs, read saved rows, and return a result.
3. `_fetch`: makes exactly one HTTP request, filters pull requests by the
   `pull_request` key, and selects number, title, and browser URL.
4. `SCHEMA` and `UPSERT`: the database definition and SQL write statement.
   Question marks are parameter placeholders, not string interpolation.
5. `read_issues`: only opens the database and selects stored issues. There is
   no `_fetch` call, which is why it works offline.
6. `_result` and `_failure`: keep success and failure outputs predictable for
   another program that wants to use the connector.

`with connection` commits or rolls back a transaction. `closing(connection)`
closes the database connection afterward. These are separate responsibilities.

## Decisions you should be ready to explain

- **Why Python?** Built-in HTTP, JSON, SQLite, and testing libraries meet the
  brief with no extra dependency setup.
- **Why SQLite?** Data must persist locally after the program exits. SQLite
  stores data in a file and supports uniqueness constraints and transactions.
- **Why repository plus issue number?** Different repositories can each have
  issue #1. Issue number alone would mix their data.
- **Why not delete missing issues?** Only one API page is fetched. A previously
  imported issue can move off page 1 without being closed. The connector
  retains earlier records, so it is not a full current-open-issues sync.
- **Why mocked tests?** They run without internet and reliably reproduce
  duplicate imports, mixed issues/PRs, HTTP failures, and malformed responses.
  The demo provides separate evidence of a real integration.
- **How do failures protect data?** Fetch and response validation happen before
  storage changes; SQLite rolls back a batch if any write fails.

## Practice without looking at the answer

1. Find the exact line that excludes pull requests. What would happen without it?
2. Explain the difference between `count` and `imported_count`.
3. Change a test fixture's issue title, import twice, and explain why the row
   count stays the same while the title changes.
4. Find the test that starts a new process. Why is it stronger evidence of
   persistence than reading through the original connection?
5. What would you add for a full synchronization system? Think pagination,
   closed-issue handling, timestamps, retries, and rate-limit behavior.

The AI disclosure is part of the assessment. Describe the assistance accurately
and show that you verified it; do not claim you wrote every line unaided.
