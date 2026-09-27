"""콘테스트코리아 (contestkorea.com) 대회·공모전 목록. Listing facts only (see crawler/contests_common.py).

Server-rendered HTML, 100 rows a page (int_gbn=1 = 대회·공모전). Each row has category, title, 주최, 대상
('누구나 , 중학생 , 고등학생 , 해당자 ▶') and the 접수 period 'mm.dd~mm.dd' without a year. Rows are parsed one
block at a time (a pattern spanning rows swallowed neighbours when a field was missing). Newest first; the walk
stops at the first page with nothing still taking entries.
"""
import datetime as dt
import re

from .. import contests_common as cc
from ..util import today

NAME = "contestkorea"
LABEL = "콘테스트코리아 공모전"
NEEDS_KEY = False
LIST = "https://www.contestkorea.com/sub/list.php"
DETAIL = "https://www.contestkorea.com/sub/view.php?int_gbn=1&str_no={}"
OPEN = ("접수중", "접수예정", "마감임박")


def _period(rec: str):
    """'09.14~10.19' has no year: pick the year that puts the deadline nearest today (a yearly contest can keep
    an old registration number, so the number is no guide), allowing 45 days for one that just closed."""
    m = re.match(r"(\d\d)\.(\d\d)~(\d\d)\.(\d\d)", rec)
    if not m:
        return None, None
    a, b, c, d = map(int, m.groups())
    t = today()
    best = None
    for year in (t.year - 1, t.year, t.year + 1):
        try:
            cand = dt.date(year, c, d)
        except ValueError:
            continue
        days = (cand - t).days
        score = (0 if days >= -45 else 1, abs(days))
        if best is None or score < best[0]:
            best = (score, cand)
    if not best:
        return None, None
    end = best[1]
    try:
        start = dt.date(end.year, a, b)
    except ValueError:
        return None, end.isoformat()
    if start > end:
        start = start.replace(year=end.year - 1)
    return start.isoformat(), end.isoformat()


def _field(block: str, name: str) -> str:
    m = re.search(rf"<strong>{name}</strong>\s*\.\s*(.*?)</li>", block, re.S)
    return cc.clean(m.group(1)) if m else ""


def parse(page_html: str) -> list[dict]:
    rows = []
    for block in page_html.split('<div class="title">')[1:]:
        block = block[:4000]
        no = re.search(r"str_no=(\d+)", block)
        title = re.search(r'<span class="txt">(.*?)</span>', block, re.S)
        cond = re.search(r'<span class="condition"[^>]*>(.*?)</span>', block, re.S)
        if not (no and title and cond):
            continue
        cat = re.search(r'<span class="category">(.*?)</span>', block, re.S)
        rec = re.search(r"<em>접수</em>\s*([\d.~\s]+)", block)
        rows.append({"no": no.group(1), "title": title.group(1), "category": cc.clean(cat.group(1)) if cat else "",
                     "host": _field(block, "주최"), "target": _field(block, "대상"),
                     "rec": re.sub(r"\s+", "", rec.group(1)) if rec else "", "cond": cc.clean(cond.group(1))})
    return rows


def fetch():
    items = {}
    for page in range(1, cc.max_pages(NAME) + 1):
        rows = parse(cc.get(LIST, {"int_gbn": 1, "displayrow": 100, "page": page}).text)
        live = [r for r in rows if r["cond"] in OPEN]
        if not live:
            break
        for r in live:
            start, end = _period(r["rec"])
            it = cc.make_item(NAME, r["no"], title=r["title"], host=r["host"], url=DETAIL.format(r["no"]),
                              apply_start=start, apply_end=end, categories=[r["category"]] if r["category"] else [],
                              target=r["target"])
            if it:
                items[r["no"]] = it
    return list(items.values())
