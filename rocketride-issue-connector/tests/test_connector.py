import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import connector


def issue(number=1, title="Fix login", **extra):
    return {"number": number, "title": title,
            "html_url": f"https://github.com/example/project/issues/{number}", **extra}


def response(payload):
    return io.BytesIO(json.dumps(payload).encode())


class ConnectorTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.db = Path(self.directory.name) / "issues.db"
        self.repo = "example/project"

    def load(self, payload, repository=None):
        with patch("connector.urlopen", return_value=response(payload)):
            return connector.import_issues(repository or self.repo, self.db)

    def test_import_saves_required_fields_and_excludes_pull_requests(self):
        result = self.load([issue(2), issue(3, pull_request={}), issue(1)])
        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["imported_count"], 2)
        self.assertEqual(result["issues"][0], {
            "repository": self.repo, "number": 1, "title": "Fix login",
            "url": "https://github.com/example/project/issues/1"})

    def test_read_never_calls_github(self):
        imported = self.load([issue()])
        with patch("connector.urlopen", side_effect=AssertionError("Read called network")):
            result = connector.read_issues(self.repo, self.db)
        self.assertEqual(result["issues"], imported["issues"])
        self.assertIsNone(result["imported_count"])

    def test_repeated_import_updates_without_duplicates(self):
        self.load([issue(1), issue(2)])
        result = self.load([issue(1, "Updated title", html_url="https://github.com/example/project/issues/1?updated"), issue(2)])
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["issues"][0]["title"], "Updated title")
        self.assertTrue(result["issues"][0]["url"].endswith("?updated"))
        with sqlite3.connect(self.db) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM issues").fetchone()[0], 2)

    def test_repository_case_is_normalized(self):
        self.load([issue()], " Example/Project ")
        result = self.load([issue()], "EXAMPLE/PROJECT")
        self.assertEqual(result["count"], 1)
        self.assertEqual(connector.read_issues("Example/Project", self.db)["count"], 1)

    def test_repositories_are_isolated(self):
        self.load([issue()], "example/first")
        self.load([issue(1, "Other issue")], "example/second")
        self.assertEqual(connector.read_issues("example/first", self.db)["issues"][0]["title"], "Fix login")
        self.assertEqual(connector.read_issues("example/second", self.db)["issues"][0]["title"], "Other issue")

    def test_data_persists_in_new_process(self):
        self.load([issue()])
        run = subprocess.run([sys.executable, "connector.py", "read", self.repo, "--db", str(self.db)],
                             cwd=Path(connector.__file__).parent, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)["count"], 1)

    def test_api_failure_preserves_saved_data(self):
        self.load([issue()])
        with patch("connector.urlopen", side_effect=HTTPError("url", 500, "Failure", {}, None)):
            result = connector.import_issues(self.repo, self.db)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "api_error")
        self.assertIn("500", result["error"]["message"])
        self.assertEqual(connector.read_issues(self.repo, self.db)["count"], 1)

    def test_http_404_is_useful_and_does_not_create_database(self):
        with patch("connector.urlopen", side_effect=HTTPError("url", 404, "Not Found", {}, None)):
            result = connector.import_issues(self.repo, self.db)
        self.assertIn("not found", result["error"]["message"])
        self.assertFalse(self.db.exists())

    def test_access_and_rate_limit_failures(self):
        for status in (403, 429):
            with self.subTest(status=status), patch("connector.urlopen", side_effect=HTTPError("url", status, "Blocked", {}, None)):
                result = connector.import_issues(self.repo, self.db)
                self.assertEqual(result["error"]["code"], "api_error")
                self.assertIn(str(status), result["error"]["message"])

    def test_network_and_timeout_failures(self):
        for error in (URLError("offline"), TimeoutError("timeout")):
            with self.subTest(error=error), patch("connector.urlopen", side_effect=error):
                self.assertEqual(connector.import_issues(self.repo, self.db)["error"]["code"], "api_error")

    def test_invalid_repositories_fail_before_network_or_database(self):
        for repository in ("", "owner", "a/b/c", "https://github.com/a/b", "a/..", "a/hello world", "-a/b", None, 12):
            with self.subTest(repository=repository), patch("connector.urlopen") as request:
                result = connector.import_issues(repository, self.db)
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"]["code"], "invalid_repository")
                request.assert_not_called()
        self.assertFalse(self.db.exists())

    def test_invalid_read_repository(self):
        self.assertEqual(connector.read_issues("bad", self.db)["error"]["code"], "invalid_repository")

    def test_one_page_request_has_open_filter_and_timeout(self):
        with patch("connector.urlopen", return_value=response([])) as request:
            result = connector.import_issues(self.repo, self.db)
        request.assert_called_once()
        req = request.call_args.args[0]
        self.assertEqual(req.full_url, "https://api.github.com/repos/example/project/issues?state=open&per_page=100&page=1")
        self.assertEqual(request.call_args.kwargs["timeout"], 15)
        self.assertTrue(result["ok"])

    def test_empty_and_pull_request_only_pages(self):
        for payload in ([], [issue(pull_request={})]):
            result = self.load(payload)
            self.assertTrue(result["ok"])
            self.assertEqual(result["count"], 0)

    def test_read_before_import_returns_empty_list(self):
        result = connector.read_issues(self.repo, self.db)
        self.assertTrue(result["ok"])
        self.assertEqual(result["issues"], [])

    def test_bad_json_is_rejected(self):
        with patch("connector.urlopen", return_value=io.BytesIO(b"not JSON")):
            result = connector.import_issues(self.repo, self.db)
        self.assertEqual(result["error"]["code"], "invalid_response")
        self.assertFalse(self.db.exists())

    def test_malformed_payload_does_not_partially_save(self):
        self.load([issue(1, "Original")])
        for payload in ({"message": "unexpected"}, [None], [issue(1, "Changed"), {"number": 2}], [issue(True)], [issue(0)]):
            with self.subTest(payload=payload):
                result = self.load(payload)
                self.assertEqual(result["error"]["code"], "invalid_response")
                self.assertEqual(connector.read_issues(self.repo, self.db)["issues"][0]["title"], "Original")

    def test_later_page_does_not_delete_earlier_records(self):
        self.load([issue(1), issue(2)])
        result = self.load([issue(2, "Updated")])
        self.assertEqual(result["imported_count"], 1)
        self.assertEqual(result["count"], 2)

    def test_database_path_failure_is_useful(self):
        bad_path = Path(self.directory.name) / "missing" / "issues.db"
        for result in (connector.read_issues(self.repo, bad_path), self._import_to(bad_path)):
            self.assertFalse(result["ok"])
            self.assertEqual(result["error"]["code"], "database_error")

    def _import_to(self, path):
        with patch("connector.urlopen", return_value=response([issue()])):
            return connector.import_issues(self.repo, path)

    def test_memory_and_empty_database_paths_rejected(self):
        for path in ("", ":memory:", None):
            self.assertEqual(connector.read_issues(self.repo, path)["error"]["code"], "database_error")

    def test_sql_like_title_is_stored_as_plain_data(self):
        title = "'); DROP TABLE issues; -- café"
        self.load([issue(title=title)])
        self.assertEqual(connector.read_issues(self.repo, self.db)["issues"][0]["title"], title)

    def test_sql_failure_rolls_back_entire_import(self):
        self.load([issue(1, "Original")])
        with sqlite3.connect(self.db) as db:
            db.execute("""CREATE TRIGGER reject_second BEFORE INSERT ON issues
                          WHEN NEW.number = 2 BEGIN SELECT RAISE(ABORT, 'Rejected'); END""")
        result = self.load([issue(1, "Changed"), issue(2)])
        self.assertEqual(result["error"]["code"], "database_error")
        saved = connector.read_issues(self.repo, self.db)
        self.assertEqual(saved["count"], 1)
        self.assertEqual(saved["issues"][0]["title"], "Original")

    def test_consistent_json_result_shape(self):
        results = [self.load([issue()]), connector.read_issues(self.repo, self.db), connector.read_issues("bad", self.db)]
        for result in results:
            self.assertEqual(set(result), {"ok", "repository", "count", "imported_count", "issues", "error"})
            self.assertEqual(json.loads(json.dumps(result)), result)

    def test_cli_error_has_failure_exit_status_and_json(self):
        run = subprocess.run([sys.executable, "connector.py", "import", "invalid"],
                             cwd=Path(connector.__file__).parent, capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertEqual(json.loads(run.stdout)["error"]["code"], "invalid_repository")


if __name__ == "__main__":
    unittest.main()
