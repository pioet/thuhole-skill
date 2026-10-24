import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "thuhole-skill" / "scripts"))
from latest_blogs import main


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self):
        return json.dumps(self.payload).encode()


class FakeOpener:
    def __init__(self, payloads):
        self.payloads = payloads
        self.requests = []

    def __call__(self, request, timeout):
        parsed = urlparse(request.full_url)
        params = parse_qs(parsed.query)
        key = (parsed.path.rsplit("/", 1)[-1], tuple(sorted((k, v[0]) for k, v in params.items())))
        self.requests.append(key)
        return FakeResponse(self.payloads[key])


class LatestBlogsTests(unittest.TestCase):
    def test_fetches_post_details_comments_and_source_url(self):
        opener = FakeOpener({
            ("getlist", (("order_mode", "0"), ("p", "1"), ("room_id", "1"))):
                {"code": 0, "data": [{"pid": 10}, {"pid": 9}]},
            ("getone", (("pid", "10"),)):
                {"code": 0, "data": {"pid": 10, "text": "完整正文"}},
            ("getcomment", (("pid", "10"),)):
                {"code": 0, "data": [{"cid": 2, "text": "评论"}]},
        })
        output = io.StringIO()
        with redirect_stdout(output):
            main(["--limit", "1"], token="test", opener=opener)

        records = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(records, [{
            "pid": 10, "text": "完整正文",
            "url": "https://hole.thu.monster/?##10",
            "comments": [{"cid": 2, "text": "评论"}],
        }])
        self.assertEqual(len(opener.requests), 3)

    def test_fetches_next_page_to_reach_limit_without_comments(self):
        opener = FakeOpener({
            ("getlist", (("order_mode", "0"), ("p", "2"), ("room_id", "1"))):
                {"code": 0, "data": [{"pid": 8}]},
            ("getlist", (("order_mode", "0"), ("p", "3"), ("room_id", "1"))):
                {"code": 0, "data": [{"pid": 7}]},
            ("getone", (("pid", "8"),)): {"code": 0, "data": {"pid": 8, "text": "A"}},
            ("getone", (("pid", "7"),)): {"code": 0, "data": {"pid": 7, "text": "B"}},
        })
        output = io.StringIO()
        with redirect_stdout(output):
            main(["--page", "2", "--limit", "2", "--no-comments"], token="test", opener=opener)

        records = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual([record["pid"] for record in records], [8, 7])
        self.assertTrue(all("comments" not in record for record in records))
        self.assertEqual(len(opener.requests), 4)


if __name__ == "__main__":
    unittest.main()
