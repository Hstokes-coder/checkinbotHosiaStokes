# INF601 - Advanced Programming in Python
# Hosia Stokes
# Scheduled Check-In Bot

"""
checkin_bot.py  (Task 2)

Looks at every post from the instructor (author_id=INSTRUCTOR_ID),
finds the ones whose title contains "check-in" (case-insensitive),
and replies to each one with a comment - unless we've already replied
to it, or the reply window has closed (HTTP 423).

Run it with:
    python checkin_bot.py
"""

import os

from dotenv import load_dotenv

from practice_hub_client import PracticeHubClient, load_config

load_dotenv()

API_URL, API_TOKEN, INSTRUCTOR_ID = load_config()

# The comment the bot will post for an open check-in.
REPLY_BODY = "Checked in."


def is_check_in(post):
    """
    A post counts as a check-in if "check-in" appears anywhere in its
    (lowercased) title - the exact detection rule the assignment
    specifies. .lower() means "Check-In", "CHECK-IN", and "check-in"
    all match the same way.
    """
    return "check-in" in post.get("title", "").lower()


def comment_author_id(comment):
    """
    Pull the author's id out of one comment.

    We've confirmed posts use the field name "author_id", but we
    haven't yet seen a real comment's JSON, so this tries that same
    name first, then a couple of common alternates, before giving up.
    If none of them match, it raises a clear error naming the actual
    comment data - much easier to debug than a comparison that just
    silently never matches anything.
    """
    for key in ("author_id", "user_id", "id"):
        if key in comment:
            return comment[key]

    author = comment.get("author")
    if isinstance(author, dict) and "id" in author:
        return author["id"]

    raise ValueError(
        f"Couldn't find an author id on this comment: {comment!r}. "
        "Inspect a real comment's fields and update comment_author_id()."
    )


def already_replied(client, post_id, my_user_id):
    """
    True if one of this post's existing comments was authored by us.

    Fetches the post's comments fresh (no local record-keeping file -
    the assignment asks us to check the live comments each time), and
    compares each comment's author id against our own account's id.
    """
    comments = client.list_comments(post_id)
    return any(comment_author_id(comment) == my_user_id for comment in comments)


def main():
    client = PracticeHubClient(API_URL, API_TOKEN)

    # Ask the API who we are, once, up front - this is what lets
    # already_replied() recognize our own past comments below.
    me = client.get_current_user()
    my_user_id = me["id"]
    print(f"Running as {me['name']!r} (id={my_user_id})")

    # list_all_posts(author=...) filters server-side, so posts from
    # any other author never even reach this script.
    check_in_posts = [
        post for post in client.list_all_posts(author=INSTRUCTOR_ID)
        if is_check_in(post)
    ]
    print(f"Found {len(check_in_posts)} check-in post(s) from instructor {INSTRUCTOR_ID}")

    for post in check_in_posts:
        post_id = post["id"]
        title = post["title"]

        if already_replied(client, post_id, my_user_id):
            print(f"[skip] Post {post_id} ({title!r}) - already replied")
            continue

        response = client.create_comment(post_id, REPLY_BODY)

        if response.status_code == 423:
            print(f"Check-in closed, skipping (post {post_id}: {title!r})")
            continue

        response.raise_for_status()
        print(f"[replied] Post {post_id} ({title!r})")


if __name__ == "__main__":
    main()
