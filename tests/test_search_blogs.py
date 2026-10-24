import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "thuhole-skill" / "scripts"))
from search_blogs import HoleClient, HoleAPIError, main


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self):
        return json.dumps(self.data).encode()


class FakeOpener:
    def __init__(self, pages):
        self.pages = pages
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        if urlparse(request.full_url).path.endswith("/getcomment"):
            return FakeResponse(self.pages["comments"])
        page = int(parse_qs(urlparse(request.full_url).query)["page"][0])
        return FakeResponse(self.pages[page])


class HoleClientTests(unittest.TestCase):
    def test_search_page_preserves_advanced_query_and_parameters(self):
        opener = FakeOpener({3: {"code": 0, "count": 1, "data": [{"pid": 7}]}})
        client = HoleClient("secret", opener=opener)
        page = client.search_page('+(贵系 雷系) +post_id:[700000 TO *]', page=3, page_size=100)
        request, timeout = opener.requests[0]
        params = parse_qs(urlparse(request.full_url).query)
        self.assertEqual(page["data"][0]["pid"], 7)
        self.assertEqual(params["keywords"], ['+(贵系 雷系) +post_id:[700000 TO *]'])
        self.assertEqual(params["page"], ["3"])
        self.assertEqual(params["pagesize"], ["100"])
        self.assertEqual(params["search_mode"], ["1"])
        self.assertEqual(request.get_header("User-token"), "secret")
        self.assertEqual(timeout, 15)

    def test_iter_search_continues_until_empty_page_even_when_page_is_short(self):
        opener = FakeOpener({
            1: {"code": 0, "count": 1, "data": [{"pid": 3}]},
            2: {"code": 0, "count": 1, "data": [{"pid": 2}]},
            3: {"code": 0, "count": 0, "data": []},
        })
        client = HoleClient("secret", opener=opener)
        self.assertEqual([p["pid"] for p in client.iter_search("具身", page_size=50)], [3, 2])
        self.assertEqual(len(opener.requests), 3)

    def test_iter_search_stops_at_max_pages(self):
        opener = FakeOpener({1: {"code": 0, "data": [{"pid": 3}]}})
        client = HoleClient("secret", opener=opener)
        self.assertEqual([p["pid"] for p in client.iter_search("具身", max_pages=1)], [3])
        self.assertEqual(len(opener.requests), 1)

    def test_iter_search_rejects_repeated_page(self):
        repeated = {"code": 0, "data": [{"pid": 3}]}
        client = HoleClient("secret", opener=FakeOpener({1: repeated, 2: repeated}))
        with self.assertRaisesRegex(HoleAPIError, "repeated"):
            list(client.iter_search("具身"))

    def test_search_page_rejects_api_error(self):
        client = HoleClient("secret", opener=FakeOpener({1: {"code": 401, "msg": "expired"}}))
        with self.assertRaisesRegex(HoleAPIError, "expired"):
            client.search_page("具身")

    def test_search_page_reports_http_authentication_error(self):
        def unauthorized(_request, timeout):
            raise HTTPError("https://api.new-t.dev", 401, "Unauthorized", {}, None)

        client = HoleClient("expired", opener=unauthorized)
        with self.assertRaisesRegex(HoleAPIError, "401"):
            client.search_page("具身")

    def test_search_page_distinguishes_network_failure_from_token_failure(self):
        def unreachable(_request, timeout):
            raise URLError(OSError(8, "nodename nor servname provided, or not known"))

        client = HoleClient("valid-or-not-unknown", opener=unreachable)
        with self.assertRaisesRegex(HoleAPIError, "token was not checked"):
            client.search_page("具身")

    def test_get_comments_returns_full_comment_list(self):
        opener = FakeOpener({"comments": {"code": 0, "data": [{"cid": 8, "text": "观点"}]}})
        client = HoleClient("secret", opener=opener)
        self.assertEqual(client.get_comments(743064)[0]["text"], "观点")
        self.assertEqual(parse_qs(urlparse(opener.requests[0][0].full_url).query)["pid"], ["743064"])

    def test_search_page_rejects_unknown_mode(self):
        client = HoleClient("secret", opener=FakeOpener({}))
        with self.assertRaisesRegex(ValueError, "search_mode"):
            client.search_page("具身", search_mode=3)

    def test_cli_emits_json_lines(self):
        opener = FakeOpener({
            1: {"code": 0, "data": [{"pid": 3, "text": "具身实习"}]},
            2: {"code": 0, "data": []},
        })
        output = io.StringIO()
        with redirect_stdout(output):
            main(["具身", "--all-pages", "--no-comments"], token="secret", opener=opener)
        self.assertEqual(json.loads(output.getvalue())["url"], "https://hole.thu.monster/?##3")

    def test_cli_with_comments_enriches_each_post(self):
        opener = FakeOpener({
            1: {"code": 0, "data": [{"pid": 3, "text": "具身"}]},
            "comments": {"code": 0, "data": [{"cid": 8, "text": "观点"}]},
        })
        output = io.StringIO()
        with redirect_stdout(output):
            main(["具身", "--with-comments"], token="secret", opener=opener)
        self.assertEqual(json.loads(output.getvalue())["comments"][0]["text"], "观点")

    def test_cli_since_filters_dates_after_scanning_all_pages(self):
        opener = FakeOpener({
            1: {"code": 0, "data": [{"pid": 3, "timestamp": 100}]},
            2: {"code": 0, "data": [{"pid": 2, "timestamp": 90000}]},
            3: {"code": 0, "data": []},
        })
        output = io.StringIO()
        with redirect_stdout(output):
            main(["具身", "--all-pages", "--no-comments", "--since", "1970-01-02T00:00:00+00:00"],
                 token="secret", opener=opener)
        self.assertEqual(json.loads(output.getvalue())["pid"], 2)
        self.assertEqual(len(opener.requests), 3)


if __name__ == "__main__":
    unittest.main()
