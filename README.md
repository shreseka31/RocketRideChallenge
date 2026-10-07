
# RocketRide GitHub Issue Snapshot Connector

## Overview

For this challenge, I built a small Python connector that imports open issues from a public GitHub repository and stores them in a local SQLite database.

The connector supports two main operations:

- **Import issues** from GitHub using the `owner/repository` format
- **Read saved issues** directly from SQLite without making another GitHub API request

I also made sure repeated imports do not create duplicate issues, and that invalid repositories or API errors return useful structured error messages.

## How it works

The basic flow is:

```text
GitHub Issues API
        |
        v
Python connector
        |
        v
SQLite database
        |
        v
Local/offline read
```

For each issue, I save:

- repository
- issue number
- title
- GitHub URL

Pull requests returned by the GitHub Issues API are filtered out so only actual issues are stored.

## Requirements

I developed and tested this project using:

- Python 3.9
- SQLite
- pytest
- Git
- GitHub

Most of the connector uses Python's standard library.

## Local setup

Clone the repository:

```bash
git clone https://github.com/shreseka31/RocketRideChallenge.git
cd RocketRideChallenge
```

Install the test dependency if needed:

```bash
python3 -m pip install pytest
```

## Run the demo

To run the connector against a real public GitHub repository:

```bash
python3 demo.py pallets/itsdangerous --db rehearsal.db --pause
```

The demo walks through four cases:

1. A real GitHub issue import
2. Reading the saved issues in a new process
3. Importing the same repository again to verify there are no duplicates
4. Passing an invalid repository to demonstrate error handling

### Example import result

```json
{
  "ok": true,
  "repository": "pallets/itsdangerous",
  "count": 3,
  "imported_count": 3,
  "issues": [
    {
      "repository": "pallets/itsdangerous",
      "number": 389,
      "title": "serializer_kwargs are missing in load_payload function",
      "url": "https://github.com/pallets/itsdangerous/issues/389"
    }
  ],
  "error": null
}
```

The exact number of open issues may change because this is a live GitHub repository.

### Example invalid input

Input:

```text
invalid-repository
```

Result:

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

## Running the tests

Run:

```bash
python3 -m pytest -q
```

At the time I completed the project, all tests passed:

```text
24 passed
```

The tests cover areas including:

- importing issues
- reading saved issues
- repeated imports without duplicates
- invalid repository input
- API failures

The GitHub API is mocked in the automated tests so the tests are repeatable and do not depend on GitHub being available.

The demo uses a real GitHub API request.

## Design decisions

### SQLite

I used SQLite because the challenge only needs local persistence. It is lightweight, requires no separate database server, and allows the saved issues to remain available after the Python process exits.

### Separate import and read behavior

I kept importing and reading separate.

The import operation is responsible for communicating with GitHub and saving the snapshot.

The read operation only accesses SQLite. It does not need GitHub, which makes it possible to read previously saved data offline.

### Preventing duplicates

A repeated import should not create another copy of the same issue. I use the repository and issue number to identify an issue that has already been stored.

This allows the connector to update an existing record instead of inserting a duplicate.

## AI and other tools I used

### ChatGPT

I used ChatGPT while working through the challenge to:

- understand the GitHub Issues API behavior
- think through the connector structure
- help debug Python and environment errors
- review test cases
- troubleshoot an SSL certificate problem on my Mac
- review whether my demo covered the challenge requirements

I did not just rely on generated answers. I ran the code, inspected the output, reran the tests, checked the SQLite behavior, and corrected issues when the actual results were different from what I expected.

### GitHub

I used GitHub for:

- the public Issues API
- source control
- storing the final project repository

### Git

I used Git locally to track and push the project.

### pytest

I used pytest for the automated test suite.

### SQLite

I used SQLite for persistent local storage of imported issues.

### Terminal

I used the macOS terminal to run the application, tests, Git commands, and debugging commands.

## One unfamiliar problem I solved with AI

One issue I ran into was an SSL certificate error when Python tried to make the real HTTPS request to GitHub.

At first, I tried to run the Python `Install Certificates.command` script, but that script did not exist at the expected location on my machine.

I used ChatGPT to help investigate the environment and discovered that I had multiple Python environments involved, including Conda and a Python 3.9 installation.

I updated the certificate package and used Python's `certifi` certificate bundle for the HTTPS connection.

I did not assume the fix worked just because the command completed. I verified it by directly making an HTTPS request to:

```text
https://api.github.com
```

and confirmed that it returned HTTP status `200`.

After that, I reran the real connector demo and confirmed that it successfully imported the GitHub issues.

This was useful because it showed me the difference between fixing an environment problem and actually verifying that the application works afterward.

## Verification

Before completing the challenge, I verified the connector by:

- making a real GitHub API import
- confirming the issues were written to SQLite
- reading them again in a new process
- importing the same repository twice and confirming there were zero duplicates
- testing invalid input
- running the complete automated test suite

Final automated test result:

```text
24 passed
```

## Architecture

See [Architecture.MD](Architecture.MD) for more detail about the connector interface, database schema, API-to-database flow, configuration, error handling, and design tradeoffs.
