"""Run the four assessment demo steps against the real GitHub API."""

import argparse
import json
from pathlib import Path
import sqlite3
import subprocess
import sys


def run(command, repository, db):
    # Each command runs in a new process to demonstrate persistence on restart.
    process = subprocess.run(
        [sys.executable, "connector.py", command, repository, "--db", db],
        cwd=Path(__file__).parent, capture_output=True, text=True,
    )
    if not process.stdout:
        raise RuntimeError(process.stderr)
    result = json.loads(process.stdout)
    preview = {**result, "issues": result["issues"][:2]}
    print(json.dumps(preview, indent=2), flush=True)
    if result["count"] > 2:
        print(f"Showing 2 of {result['count']} saved issues. The connector returns all saved issues.", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", nargs="?", default="pallets/itsdangerous")
    parser.add_argument("--db", default="demo.db")
    parser.add_argument("--pause", action="store_true", help="Press Enter between steps while recording")
    args = parser.parse_args()
    # Resolve before starting child processes, which use the project directory.
    db = str(Path(args.db).resolve())
    steps = [("1. REAL GitHub import", "import", args.repository),
             ("2. Offline read in a NEW process", "read", args.repository),
             ("3. Repeated real import", "import", args.repository),
             ("4. Invalid repository error", "import", "invalid-repository")]
    for title, command, repository in steps:
        if args.pause:
            input(f"\nPress Enter for {title}: ")
        print(f"\n{title}", flush=True)
        result = run(command, repository, db)
        if repository == args.repository and not result["ok"]:
            return 1
        if command == "import" and repository == args.repository:
            with sqlite3.connect(db) as connection:
                total, unique = connection.execute(
                    "SELECT COUNT(*), COUNT(DISTINCT number) FROM issues WHERE repository = ?",
                    (result["repository"],),
                ).fetchone()
            print(f"Database rows: {total}; unique issue numbers: {unique}; duplicates: {total - unique}", flush=True)
        if repository == "invalid-repository" and (result["ok"] or result["error"]["code"] != "invalid_repository"):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
