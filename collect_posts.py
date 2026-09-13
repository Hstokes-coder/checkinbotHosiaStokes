
# INF601 - Advanced Programming in Python
# Hosia Stokes
# Scheduled Check-In Bot
 
"""
collect_posts.py  (Task 1)
 
Paginates through every post written by the instructor
(author=INSTRUCTOR_ID), records title/body/tags/timestamps for each
one, downloads every attachment to artifact/files/, and writes it all
to artifact/collected.json.
 
Run it with:
    python collect_posts.py
"""
 
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse
 
from dotenv import load_dotenv
 
from practice_hub_client import PracticeHubClient, load_config
 
# Loads variables from a local .env file into os.environ, if one
# exists. In GitHub Actions there is no .env file - the secrets/vars
# are already in the environment - so this line is simply a no-op there.
load_dotenv()
 
API_URL, API_TOKEN, INSTRUCTOR_ID = load_config()
 
ARTIFACT_DIR = Path("artifact")
FILES_DIR = ARTIFACT_DIR / "files"
COLLECTED_PATH = ARTIFACT_DIR / "collected.json"
 
 
def safe_filename(name):
    """
    Strip anything that isn't safe in a filename: path separators
    (so an attachment name can't write outside artifact/files/) and
    control characters. Falls back to "attachment" if nothing is left.
    """
    name = name.strip().replace("/", "_").replace("\\", "_")
    name = re.sub(r'[<>:"|?*\x00-\x1f]', "_", name)
    return name or "attachment"
 
 
def resolve_filename(attachment, response):
    """
    Decide what to name a downloaded attachment on disk. We don't yet
    know exactly which of these fields the real API provides, so we
    try each option in order of preference and use the first one that
    works:
 
      1. attachment["filename"], if the API includes it directly
      2. the filename in the response's Content-Disposition header
      3. the last path segment of the download URL
      4. a fallback built from the attachment's id
    """
    if attachment.get("filename"):
        return safe_filename(attachment["filename"])
 
    content_disposition = response.headers.get("Content-Disposition", "")
    match = re.search(r'filename="?([^";]+)"?', content_disposition)
    if match:
        return safe_filename(match.group(1))
 
    url_path = urlparse(attachment["download_url"]).path
    tail = Path(url_path).name
    if tail:
        return safe_filename(tail)
 
    return safe_filename(f"attachment_{attachment.get('id', 'unknown')}")
 
 
def collect_attachments(client, post, files_dir):
    """
    Download every attachment listed on one post.
 
    Returns a list of attachment records: each is the original
    attachment data from the API, plus a "local_path" key pointing at
    where we saved the file. Called once per post from main().
    """
    saved = []
    for attachment in post.get("attachments", []):
        response = client.download_attachment(attachment["download_url"])
        filename = resolve_filename(attachment, response)
 
        local_path = files_dir / filename
        local_path.write_bytes(response.content)
 
        saved.append({
            **attachment,
            "local_path": str(local_path.as_posix()),
        })
    return saved
 
 
def main():
    # exist_ok=True: fine if artifact/files/ already exists from a
    # previous run; parents=True also creates artifact/ if it's missing.
    FILES_DIR.mkdir(parents=True, exist_ok=True)
 
    client = PracticeHubClient(API_URL, API_TOKEN)
 
    collected = []
    for post in client.list_all_posts(author=INSTRUCTOR_ID):
        attachments = collect_attachments(client, post, FILES_DIR)
 
        collected.append({
            "id": post.get("id"),
            "title": post.get("title"),
            "body": post.get("body"),
            "tags": post.get("tags"),
            "created_at": post.get("created_at"),
            "updated_at": post.get("updated_at"),
            "attachments": attachments,
        })
 
    COLLECTED_PATH.write_text(json.dumps(collected, indent=2))
 
    print(f"Collected {len(collected)} posts from instructor {INSTRUCTOR_ID}")
    print(f"Wrote {COLLECTED_PATH}")
 
 
if __name__ == "__main__":
    main()
 