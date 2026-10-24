"""Read New T Hole's latest posts and their comments as JSON Lines."""

import argparse
import json
import os
from urllib.request import urlopen

from hole_client import HoleAPIError, HoleClient


def main(argv=None, *, token=None, opener=urlopen):
    parser = argparse.ArgumentParser(description="Read latest New T Hole posts; emit JSON Lines")
    parser.add_argument("--page", type=int, default=1, help="Starting page (default: 1)")
    parser.add_argument("--limit", type=int, default=25, help="Maximum posts (default: 25)")
    parser.add_argument("--room-id", type=int, default=1)
    parser.add_argument("--no-comments", action="store_true", help="Skip fetching comments")
    args = parser.parse_args(argv)
    if args.page < 1 or args.limit < 1 or args.room_id < 1:
        parser.error("--page, --limit, and --room-id must be positive")
    token = token or os.environ.get("HOLE_USER_TOKEN")
    if not token:
        parser.error("set HOLE_USER_TOKEN to your own User-Token")

    client = HoleClient(token, opener=opener)
    emitted = 0
    page = args.page
    previous_ids = None
    try:
        while emitted < args.limit:
            posts = client.latest_page(page=page, room_id=args.room_id)
            if not posts:
                break
            ids = tuple(post["pid"] for post in posts)
            if ids == previous_ids:
                raise HoleAPIError("Latest-post API repeated a page; pagination cannot continue safely")
            previous_ids = ids
            for post in posts:
                if emitted >= args.limit:
                    break
                record = client.get_post(post["pid"])
                record["url"] = f"https://hole.thu.monster/?##{post['pid']}"
                if not args.no_comments:
                    record["comments"] = client.get_comments(post["pid"])
                print(json.dumps(record, ensure_ascii=False))
                emitted += 1
            page += 1
    except (HoleAPIError, ValueError, KeyError) as exc:
        parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__":
    main()
