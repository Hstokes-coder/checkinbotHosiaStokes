# INF601 - Advanced Programming in Python
# Hosia Stokes
# Scheduled Check-In Bot

"""
practice_hub_client.py

A small wrapper around the Practice Hub API's HTTP endpoints.

This class only knows how to talk to the API:
- build requests
- attach the auth token
- return response data
- raise useful errors when something goes wrong

Task-specific logic lives in other files such as collect_posts.py.
"""

import os
from urllib.parse import urljoin

import requests


def load_config():
    """
    Read and validate PRACTICE_API_URL, PRACTICE_API_TOKEN, and
    INSTRUCTOR_ID from the environment.

    Both collect_posts.py and checkin_bot.py need the same three
    values, so this lives here once instead of being copy-pasted into
    each script. Raises a RuntimeError with a specific, actionable
    message the moment something is missing or malformed, instead of
    letting a bare os.environ[...] raise a raw KeyError (or int(...)
    raise a raw ValueError) partway through the program.

    Returns (api_url, api_token, instructor_id).
    """
    api_url = os.environ.get("PRACTICE_API_URL", "").strip()
    if not api_url:
        raise RuntimeError(
            "PRACTICE_API_URL is not set. Copy .env.example to .env and "
            "fill in your values (or set it as a GitHub Actions secret)."
        )

    api_token = os.environ.get("PRACTICE_API_TOKEN", "").strip()
    if not api_token:
        raise RuntimeError(
            "PRACTICE_API_TOKEN is not set. Copy .env.example to .env and "
            "fill in your values (or set it as a GitHub Actions secret)."
        )

    raw_instructor_id = os.environ.get("INSTRUCTOR_ID", "7").strip()
    try:
        instructor_id = int(raw_instructor_id)
    except ValueError:
        raise RuntimeError(
            "INSTRUCTOR_ID must be a whole number, got "
            f"{raw_instructor_id!r} instead."
        ) from None

    return api_url, api_token, instructor_id


class PracticeHubClient:
    """Thin HTTP client for the Practice Hub API."""

    def __init__(self, base_url, token):
        """
        base_url: the Practice Hub root URL
        token: the API token for your account
        """
        self.base_url = base_url.rstrip("/")

        # Remove accidental spaces or newlines from a copied token.
        clean_token = token.strip()

        if not clean_token:
            raise ValueError("PRACTICE_API_TOKEN is empty.")

        self.headers = {
            "Authorization": f"Bearer {clean_token}"
        }

    def _request(self, method, path, **kwargs):
        """
        Internal helper used by the other API methods.
        """
        url = f"{self.base_url}{path}"

        response = requests.request(
            method,
            url,
            headers=self.headers,
            **kwargs
        )

        return response

    # ---- Posts --------------------------------------------------------

    def list_posts(self, author=None, limit=100, offset=0):
        """
        Fetch one page of posts from GET /api/v1/posts.
        """
        params = {
            "limit": limit,
            "offset": offset
        }

        if author is not None:
            params["author"] = author

        response = self._request(
            "GET",
            "/api/v1/posts",
            params=params
        )

        if response.status_code == 401:
            raise RuntimeError(
                "Practice Hub returned 401 Unauthorized. "
                "Check that PRACTICE_API_TOKEN is set to your valid token."
            )

        response.raise_for_status()

        return response.json()

    def list_all_posts(self, author=None, limit=100):
        """
        Yield every post across all pages.
        """
        offset = 0

        while True:
            page = self.list_posts(
                author=author,
                limit=limit,
                offset=offset
            )

            posts = self._extract_posts(page)

            if not posts:
                break

            for post in posts:
                yield post

            if len(posts) < limit:
                break

            offset += limit

    @staticmethod
    def _extract_posts(page):
        """
        Convert the API response into a plain list of posts.
        """
        if isinstance(page, list):
            return page

        if isinstance(page, dict) and "results" in page:
            return page["results"]

        raise ValueError(
            "Unexpected /api/v1/posts response shape: "
            f"{type(page)} with keys "
            f"{list(page) if isinstance(page, dict) else 'n/a'}. "
            "Update _extract_posts() once you've seen a real response."
        )

    # ---- Identity -------------------------------------------------------

    def get_current_user(self):
        """
        Get the account that owns this API token from GET /api/v1/me.
        """
        response = self._request(
            "GET",
            "/api/v1/me"
        )

        if response.status_code == 401:
            raise RuntimeError(
                "Practice Hub returned 401 Unauthorized. "
                "Check that PRACTICE_API_TOKEN is set to your valid token."
            )

        response.raise_for_status()

        return response.json()

    # ---- Comments -----------------------------------------------------

    def list_comments(self, post_id):
        """
        Get all comments for one post.
        """
        response = self._request(
            "GET",
            f"/api/v1/posts/{post_id}/comments"
        )

        response.raise_for_status()

        return response.json()

    def create_comment(self, post_id, body):
        """
        Create a comment on a post.

        Returns the raw response because Task 2 needs to check
        specifically for HTTP 423.
        """
        response = self._request(
            "POST",
            f"/api/v1/posts/{post_id}/comments",
            json={"body": body}
        )

        return response

    # ---- Attachments --------------------------------------------------

    def download_attachment(self, download_url):
        """
        Download an attachment using its download URL.

        The API sometimes returns a full URL (e.g.
        "https://practice.fhsucyber.com/api/v1/attachments/2") and
        sometimes a relative path (e.g. "/api/v1/attachments/2").
        urljoin resolves a relative path against self.base_url; a
        download_url that's already absolute is returned unchanged.
        """
        url = urljoin(self.base_url.rstrip("/") + "/", download_url)

        response = requests.get(
            url,
            headers=self.headers
        )

        if response.status_code == 401:
            raise RuntimeError(
                "Practice Hub returned 401 Unauthorized while "
                "downloading an attachment."
            )

        response.raise_for_status()

        return response