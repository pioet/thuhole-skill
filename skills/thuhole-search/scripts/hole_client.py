"""HTTP client for New T Hole's observed search endpoint."""

import argparse
import json
import os
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = "https://api.new-t.dev/_api/v1/search"
LIST_URL = "https://api.new-t.dev/_api/v1/getlist"
POST_URL = "https://api.new-t.dev/_api/v1/getone"
COMMENT_URL = "https://api.new-t.dev/_api/v1/getcomment"


class HoleAPIError(RuntimeError):
    """The search API returned an invalid or unsuccessful response."""


class HoleClient:
    def __init__(self, token, *, opener=urlopen, timeout=15):
        if not token:
            raise ValueError("A User-Token is required")
        self.token = token
        self.opener = opener
        self.timeout = timeout

    def _get_json(self, url, *, data_type=list):
        request = Request(url, headers={
            "User-Token": self.token,
            "Accept": "*/*",
            "Origin": "https://hole.thu.monster",
            "Referer": "https://hole.thu.monster/",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/155.0.0.0 Safari/537.36"
            ),
        })
        try:
            with self.opener(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except HTTPError as exc:
            exc.close()
            raise HoleAPIError(f"HTTP {exc.code}: check the token or try again later") from exc
        except URLError as exc:
            raise HoleAPIError(f"Network error before authentication; token was not checked: {exc.reason}") from exc
        except (ValueError, UnicodeDecodeError) as exc:
            raise HoleAPIError("API returned non-JSON data; check the token") from exc
        if not isinstance(payload, dict) or payload.get("code") != 0:
            message = payload.get("msg", payload.get("message", "unknown error")) if isinstance(payload, dict) else "invalid response"
            raise HoleAPIError(f"API error: {message}")
        if not isinstance(payload.get("data"), data_type):
            raise HoleAPIError(f"API response has no data {data_type.__name__}")
        return payload

    def latest_page(self, *, page=1, room_id=1):
        """Return a page of posts in the site's latest order."""
        if page < 1 or room_id < 1:
            raise ValueError("page and room_id must be positive")
        params = urlencode({"p": page, "order_mode": 0, "room_id": room_id})
        return self._get_json(f"{LIST_URL}?{params}")["data"]

    def get_post(self, pid):
        """Return one complete post."""
        if pid < 1:
            raise ValueError("pid must be positive")
        return self._get_json(
            f"{POST_URL}?{urlencode({'pid': pid})}", data_type=dict,
        )["data"]

    def search_page(self, query, *, page=1, page_size=50, room_id=1, search_mode=1):
        """Return one raw API page. Search syntax is passed through unchanged."""
        if not query or not query.strip():
            raise ValueError("query must not be empty")
        if page < 1 or page_size < 1 or room_id < 1:
            raise ValueError("page, page_size, and room_id must be positive")
        if search_mode not in (0, 1, 2):
            raise ValueError("search_mode must be 0 (Tag), 1 (full text), or 2 (title)")
        params = urlencode({
            "search_mode": search_mode,
            "page": page,
            "room_id": room_id,
            "keywords": query,
            "pagesize": page_size,
        })
        return self._get_json(f"{API_URL}?{params}")

    def get_comments(self, pid):
        """Return all comments for one post."""
        if pid < 1:
            raise ValueError("pid must be positive")
        return self._get_json(f"{COMMENT_URL}?{urlencode({'pid': pid})}")["data"]

    def iter_search(self, query, *, start_page=1, page_size=50, room_id=1,
                    search_mode=1, max_pages=None):
        """Yield every result until an empty page; count is not a total."""
        if start_page < 1 or (max_pages is not None and max_pages < 1):
            raise ValueError("start_page and max_pages must be positive")
        previous_ids = None
        index = 0
        while max_pages is None or index < max_pages:
            result = self.search_page(
                query, page=start_page + index, page_size=page_size,
                room_id=room_id, search_mode=search_mode,
            )
            posts = result["data"]
            if not posts:
                return
            ids = tuple(post.get("pid") for post in posts)
            if ids == previous_ids:
                raise HoleAPIError("Search API repeated a page; pagination cannot continue safely")
            previous_ids = ids
            yield from posts
            index += 1


def main(argv=None, *, token=None, opener=urlopen):
    parser = argparse.ArgumentParser(description="Search New T Hole; emit JSON Lines")
    parser.add_argument("query", help="Full-text query, including the site's advanced syntax")
    parser.add_argument("--page", type=int, default=1, help="First page (default: 1)")
    parser.add_argument("--page-size", type=int, default=50, help="Requested page size (server may ignore it)")
    parser.add_argument("--room-id", type=int, default=1)
    parser.add_argument("--search-mode", type=int, default=1, help="1 = full-text search")
    parser.add_argument("--all-pages", action="store_true", help="Continue until an empty page")
    parser.add_argument("--max-pages", type=int, help="Safety limit with --all-pages")
    parser.add_argument("--with-comments", dest="with_comments", action="store_true", default=True,
                        help="Fetch each post's full comment list (default: on)")
    parser.add_argument("--no-comments", dest="with_comments", action="store_false",
                        help="Skip fetching comments")
    parser.add_argument("--since", help="Keep posts at or after this ISO 8601 datetime with timezone")
    args = parser.parse_args(argv)
    since_timestamp = None
    if args.since:
        try:
            since = datetime.fromisoformat(args.since)
        except ValueError:
            parser.error("--since must be an ISO 8601 datetime with timezone")
        if since.tzinfo is None:
            parser.error("--since must include a timezone offset")
        since_timestamp = since.timestamp()
    token = token or os.environ.get("HOLE_USER_TOKEN")
    if not token:
        parser.error("set HOLE_USER_TOKEN to your own User-Token")
    client = HoleClient(token, opener=opener)
    try:
        if args.all_pages:
            posts = client.iter_search(
                args.query, start_page=args.page, page_size=args.page_size,
                room_id=args.room_id, search_mode=args.search_mode,
                max_pages=args.max_pages,
            )
        else:
            posts = client.search_page(
                args.query, page=args.page, page_size=args.page_size,
                room_id=args.room_id, search_mode=args.search_mode,
            )["data"]
        for post in posts:
            if since_timestamp is not None and post.get("timestamp", 0) < since_timestamp:
                continue
            record = dict(post)
            record["url"] = f"https://hole.thu.monster/?##{post['pid']}"
            if args.with_comments:
                record["comments"] = client.get_comments(post["pid"])
            print(json.dumps(record, ensure_ascii=False))
    except (HoleAPIError, ValueError) as exc:
        parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__":
    main()
