# Scheduled Check-In Bot

An automated bot for the INF601 Practice Hub API that collects an instructor's
posts and automatically replies to any post recognized as a "check-in."

## What it does

The project has two scripts, both built on a shared API client
(`practice_hub_client.py`), plus a GitHub Actions workflow that runs them on
a schedule:

- `collect_posts.py` (Task 1) archives every post from the instructor account
  into `artifact/collected.json` and downloads any attachments.
- `checkin_bot.py` (Task 2) finds instructor posts titled as a check-in and
  replies to each one exactly once.

## How to Run

Both scripts are meant to be run from Terminal, from inside this project
folder (`checkinbotHosiaStokes`).

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

This installs `requests` (for calling the API) and `python-dotenv` (for
loading environment variables from a `.env` file).

### 2. Set up your environment variables

Copy the example file and fill in your own values - never commit the real
`.env` file (it's already listed in `.gitignore`):

```bash
cp .env.example .env
```

Then edit `.env` so it looks like this, with your own real token in place of
the placeholder:

```
PRACTICE_API_URL=https://practice.fhsucyber.com
PRACTICE_API_TOKEN=your-own-token-here
INSTRUCTOR_ID=7
```

### 3. Run Task 1 - collect posts

```bash
python3 collect_posts.py
```

This paginates through the instructor's posts, downloads any attachments
into `artifact/files/`, and writes `artifact/collected.json`. Example
output:

```
Collected 0 posts from instructor 7
Wrote artifact/collected.json
```

(The count will be higher once the instructor has posted something.)

### 4. Run Task 2 - reply to check-ins

```bash
python3 checkin_bot.py
```

This checks the same instructor's posts for any titled with "check-in,"
replies to new ones, and skips ones it's already replied to. Example
output:

```
Running as 'Hosia Stokes' (id=14)
Found 0 check-in post(s) from instructor 7
```

The two scripts are independent and can be run in either order - Task 1
does not need to run before Task 2.

## Task 1 - `collect_posts.py`

1. Reads `PRACTICE_API_URL`, `PRACTICE_API_TOKEN`, and `INSTRUCTOR_ID` from
   the environment (via a local `.env` file when run manually, or from
   GitHub Secrets/Variables when run in Actions).
2. Calls `GET /api/v1/posts?author=<INSTRUCTOR_ID>` through
   `PracticeHubClient.list_all_posts()`, which pages through the API using
   `limit`/`offset` until a page comes back with fewer posts than requested.
3. For each post, downloads every attachment (an authenticated `GET` on its
   `download_url`) into `artifact/files/`.
4. Writes a JSON array to `artifact/collected.json` with each post's `id`,
   `title`, `body`, `tags`, `created_at`, `updated_at`, and its attachment
   records (including where each file was saved locally).

## Task 2 - `checkin_bot.py`

1. Calls `GET /api/v1/me` to find out which account the API token belongs to.
2. Pulls every post from the instructor (`author=INSTRUCTOR_ID`) and keeps
   only the ones where `"check-in"` appears in the lowercased title.
3. For each check-in post, fetches its existing comments
   (`GET /api/v1/posts/{id}/comments`) and checks whether any comment's
   author id already matches the bot's own account id from step 1. If so,
   the post is skipped so it's never replied to twice.
4. If there's no existing reply, it posts a comment
   (`POST /api/v1/posts/{id}/comments`) with the body `"Checked in."`.
5. If the API responds with `423 Locked` (the reply window has closed), the
   script logs it and moves on to the next post instead of crashing.

## GitHub Actions - running every 15 minutes

`.github/workflows/checkin-bot.yml` defines the automation:

- **Triggers:** a `schedule` cron of `*/15 * * * *` (every 15 minutes, in
  UTC) plus `workflow_dispatch` for running it manually from the Actions tab.
- **Credentials:** `PRACTICE_API_TOKEN` and `PRACTICE_API_URL` come from the
  repository's encrypted **Secrets**; `INSTRUCTOR_ID` comes from the
  repository's (non-encrypted) **Variables**. None of these values are
  stored in this repo's code.
- **Steps:** check out the repo, set up Python, install
  `requirements.txt`, run `collect_posts.py`, then run `checkin_bot.py`.
- **Saving results:** the workflow stages `artifact/`, commits it only if
  something actually changed, and pushes the commit back to the repo - so
  `artifact/collected.json` and `artifact/files/` in this repo always
  reflect the most recent run.

## What's in `artifact/`

- **`artifact/collected.json`** - a JSON array (one entry per instructor
  post) produced by Task 1, containing each post's title, body, tags,
  timestamps, and a list of its attachments (each with a `local_path`
  pointing into `artifact/files/`).
- **`artifact/files/`** - the actual downloaded attachment files referenced
  by `collected.json`.

## AI Usage

I used Claude Code (via Claude's Cowork mode) as a coding assistant while
building this project. It helped with:

- Writing the initial versions of `practice_hub_client.py`,
  `collect_posts.py`, and `checkin_bot.py`, and the
  `.github/workflows/checkin-bot.yml` workflow file.
- Explaining what each function and each part of the workflow YAML does.
- Helping debug a `401 Unauthorized` error I hit when first running
  `collect_posts.py` against the real API.
- Helping me investigate why `author=7` was returning zero posts, by writing
  small diagnostic scripts to inspect the real API responses.

What I personally tested and reviewed:

- I ran `collect_posts.py` and `checkin_bot.py` against the real Practice Hub
  API myself, on my own machine, and read the actual output/tracebacks.
- I diagnosed the 401 error myself by inspecting my loaded token and testing
  it directly with `curl`, separately from the Python code.
- I ran an unfiltered API query myself and inspected the real post data to
  understand the actual `author_id`/`author_name` fields, rather than
  assuming the assignment's example instructor ID was correct.
- I made the call to keep `INSTRUCTOR_ID=7` per the assignment's spec rather
  than changing it to match whichever account looked like the instructor in
  the current test data.
- I specified the exact behavior required for Task 2 (check live comments
  for an existing reply from my own account, using `GET /api/v1/me` to
  identify "my own" comments, and the exact reply text), rather than
  accepting Claude's first suggested approach.
- I reviewed the generated code and asked follow-up questions about parts I
  wanted explained before running them.

*(This section is a draft based on our conversation - please adjust it if it
doesn't match your own experience before submitting.)*
