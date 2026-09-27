"""요즘것들 (allforyoung.com) 공모전 목록. Listing facts only (see crawler/contests_common.py).

A Next.js page: the list query (20 a page, with pagination meta) is embedded in the streamed flight data.
It has title, organization, tags (category) and a D-day, which here is exact (D-34 on 9/27 = end_at 10/31).
There is no eligibility field, so these items are judged on their title alone (mostly left for review).
Sponsored rows repeat the same posts; rows are keyed by post id. 요즘것들 blocks AI crawlers (GPTBot, ClaudeBot...)
in robots.txt; this crawler identifies as YouthBenefitFinder under `User-agent: *`, which allows /posts.
"""
import json
import re

from .. import contests_common as cc

NAME = "allforyoung"
LABEL = "요즘것들 공모전"
NEEDS_KEY = False
LIST = "https://www.allforyoung.com/posts/contest"
DETAIL = "https://www.allforyoung.com/posts/{}"
PUSH = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', re.S)


def _feed(page_html: str) -> dict:
    """The dehydrated `feed list` query: {"data": [...], "meta": {"pagination": ...}}."""
    full = "".join(json.loads(f'"{c}"') for c in PUSH.findall(page_html))
    dec = json.JSONDecoder()
    for m in re.finditer(r'\{"dehydratedAt"', full):
        try:
            obj, _ = dec.raw_decode(full, m.start())
        except ValueError:
            continue
        if "feed" in (obj.get("queryKey") or []) and isinstance(obj.get("state", {}).get("data"), dict):
            return obj["state"]["data"]
    return {}


def fetch():
    items = {}
    for page in range(1, cc.max_pages(NAME) + 1):
        feed = _feed(cc.get(LIST, {"page": page}).text)
        rows = feed.get("data") or []
        for row in rows:
            p = row.get("data") or {}
            pid = p.get("id")
            if not pid or p.get("is_expired") or pid in items:
                continue
            cats = [t.get("name", "") for t in p.get("tags") or [] if t.get("type") == "contest"]
            it = cc.make_item(NAME, pid, title=p.get("title"), host=p.get("organization"), url=DETAIL.format(pid),
                              apply_end=cc.from_dday(p.get("dday")), categories=cats)
            if it:
                items[pid] = it
        if not rows or not (feed.get("meta") or {}).get("pagination", {}).get("has_next"):
            break
    return list(items.values())
