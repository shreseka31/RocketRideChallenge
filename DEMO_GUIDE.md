# Demo and submission guide

The assessment deadline is Wednesday, October 7, 2026 at 11:59 p.m. Pacific.
Your final submission needs a GitHub repository link and a viewable Google
Drive video link. The video must be no longer than two minutes.

## Prepare first

1. Unzip the project and open Terminal in `rocketride-issue-connector`.
2. Run `python3 -m unittest discover -s tests -v`. All 24 tests should pass.
3. Run `python3 demo.py pallets/itsdangerous --db rehearsal.db` with internet
   access. Confirm imports succeed and actual issues appear. If that repository
   has no open issues, use `pallets/flask` instead.
4. Choose a new database filename for the recording, such as `recording.db`,
   so the first import starts with empty storage. Do not overwrite a database
   you want to keep.
5. Enlarge the terminal font and rehearse the explanation below. Keep the
   relevant terminal area visible and close unrelated windows.

## Record on a Mac

Press Command + Shift + 5 and choose Record Selected Portion. Under Options,
choose your microphone. Select the terminal area and start recording. Stop
using the recording control in the menu bar. If needed, trim the recording
with QuickTime Player's Edit > Trim. Watch the exported video and check its
duration and audio before uploading.

Windows alternative: record the terminal with a screen recorder already
available to you, such as Snipping Tool's recording option where supported.

## Recording sequence and suggested narration

Use `python3 demo.py pallets/itsdangerous --db recording.db --pause`.
Press Enter between the four steps. The helper uses the actual connector CLI
in a fresh Python process for every step. It does not mock the network.

| Time | Show | Suggested narration |
| --- | --- | --- |
| 0:00–0:12 | Project folder and command | “This is a Python connector that imports public GitHub issues into a local SQLite database. It uses only built-in libraries.” |
| 0:12–0:40 | Step 1 import and returned issues | “This is a real GitHub API request for one page of open issues. Pull requests are filtered out. The result shows the repository, issue number, title, and URL.” |
| 0:40–1:00 | Step 2 read | “The import process has ended. This read starts a new process and uses the same database file. It reads SQLite without calling GitHub, so the saved data persists after restart.” |
| 1:00–1:25 | Step 3 repeat import and duplicate count | “I import the repository again. The database still has zero duplicates. Repository and issue number form the primary key, and an UPSERT updates an existing issue's title and URL.” |
| 1:25–1:43 | Step 4 invalid input | “This invalid repository returns a structured error with a useful message. It fails before making a network request.” |
| 1:43–1:55 | Architecture or tests briefly | “I chose SQLite for simple persistent local storage. Automated tests check filtering, updates, offline reads, restart persistence, and API failures.” |

Use your own words. If you prefer to prove offline behavior visibly, pause
after step 1, turn off Wi-Fi, perform step 2, and restore Wi-Fi before step 3.
Rehearse this first so you stay under two minutes. Tests also verify that reads
never call the HTTP function.

The number of saved issues may increase if GitHub changes between imports.
The invariant is zero duplicate repository/issue-number pairs, not an
unchanging live issue count. Mock tests separately verify an updated title/URL.

## Publish to GitHub

Create a new empty repository named `rocketride-issue-connector` in your own
GitHub account. Make it public if the source can be shared; otherwise ensure
the reviewers have repository access. Do not initialize it with another README
if using the commands below. Then run these from the project folder, replacing
`YOUR_USERNAME` with your real GitHub username:

```bash
git init
git add .
git commit -m "Build GitHub issue snapshot connector with tests"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/rocketride-issue-connector.git
git push -u origin main
```

Follow GitHub's authentication prompts. Do not put a token or password in
source code, commands, or your recording. Alternatively, use GitHub's Upload
files action to upload the extracted source files and `tests` folder directly
to the repository root. Check that `README.md`, `Architecture.MD`,
`connector.py`, and the tests are visible at their expected paths. Upload the
source, not just the ZIP archive. Do not upload generated databases or video.

Open your repository URL in a signed-out/private browser window to confirm
reviewers can see it, or check the appropriate private-repository permissions.

## Upload the recording to Google Drive

Upload the final video, open Share, and configure viewer access for reviewers.
If your account allows it, set General access to Anyone with the link and the
role to Viewer. Copy the link. Test it in a signed-out/private browser window
and confirm the video plays. If your account restricts public sharing, grant
access to the intended reviewer and verify that access instead.

## Final checks and reply

- Source code and tests are uploaded, with README.md and Architecture.MD at root.
- README's tools section accurately reflects your process. Add other tools
  only if you actually use them.
- You have personally run the tests and real import locally.
- You can explain the functions, primary key, UPSERT, pull request filtering,
  offline reads, and cumulative snapshot limitation.
- Video is at most two minutes, includes all four steps, and is viewable.
- Reply directly to the existing email thread before the deadline. Do not use
  Reply All or start a separate message.

Suggested reply text (replace both placeholders):

Hi,

Thank you for the opportunity. Here are my RocketRide assessment submissions:

GitHub repository: [YOUR REPOSITORY LINK]

Demo video: [YOUR GOOGLE DRIVE LINK]

The repository includes the source code, automated tests, local setup
instructions, AI/tool usage notes, and Architecture.MD. The video demonstrates
a real import, saved-data retrieval, a repeated import, and error handling.

Best,
[YOUR NAME]
