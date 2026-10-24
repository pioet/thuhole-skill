---
name: thuhole-search
description: Use when searching New T Hole (新T树洞, hole.thu.monster) posts, comments, hashtags, or author titles with the bundled HTTP client.
---

# Search New T Hole

Use `scripts/hole_client.py` relative to this skill. Supply a `User-Token` through `HOLE_USER_TOKEN`; never put it in the skill, output, or committed files. The API is observed from the website and may change.

## Search workflow

1. Choose `--search-mode`: `1` full text (default), `0` Tag and folded-warning search, or `2` author-title search.
2. Use `--all-pages` for complete results. `--page` sets the starting page; `--max-pages` limits requests. The server ignored tested `--page-size` values and returned about 25 posts per page. Stop only on an empty page; a short page and `count` do not establish completion.
3. Comments are fetched by default; use `--no-comments` to skip. Full-text matches may be in comments rather than the main post. `--since` filters by post `timestamp` after retrieval; complex searches are relevance-sorted, so keep `--all-pages` for date-bounded searches.
4. Cite findings with each result's `url`. Distinguish posts and comments from verified facts.

```bash
python3 skills/thuhole-search/scripts/hole_client.py '+大模型 +实习' --all-pages --since '2026-10-17T00:00:00+08:00' --with-comments > results.jsonl
```

Set `HOLE_USER_TOKEN` in the environment before running. Each line is a JSON post with its source URL.

## Full-text query syntax

Pass the query as one quoted CLI argument. The client sends it unchanged to the server.

| Need | Query |
| --- | --- |
| Either word | `电子 直博` (equivalent to `电子 OR 直博`) |
| Grouped alternatives plus requirement | `(贵系 OR 雷系) AND 好工作` |
| Required and excluded terms | `+贵系 -雷系` |
| Required group and word | `+(贵系 雷系) +好工作` |
| Exact text, including spaces | `"and me"` or `"'鹅腿'"` |
| Search post versus comment | `content:避雷 AND comment:cy` |
| Search a field for any listed value | `content: IN [微积分 线代]` |
| Limit by post ID | `+(毕业 出二手 二手) +post_id:[700000 TO *]` |
| Boost a term | `微积分^4.0 线代` |

A single keyword sorts newest first. Complex queries, including a trailing space, sort by relevance; main-post matches weigh more than comment matches. `+微积分 线代` requires the first term and boosts matches to the second.
