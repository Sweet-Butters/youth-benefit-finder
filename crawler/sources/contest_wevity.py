"""위비티 (wevity.com) 공모전 목록. Listing facts only (see crawler/contests_common.py).

Server-rendered HTML. The list shows no eligibility, but the site filters by 응모대상, so the lists for
청소년, 대학생, 제한없음 and 일반인 are walked and a contest's target is the set of lists it appears in
(어린이 alone is not walked). Only a D-day is shown, read as today + N. The tracker once subtracted a day
(위비티 counting the deadline itself); on 2026-09-27 that put 위비티 one day before the other five sites for most
shared contests, and dropping it cut same-title-and-host date mismatches across sites from 319 to 36.
Sponsored rows repeat at the top of every page; rows are keyed by the site's ix.
"""
import re

from .. import contests_common as cc

NAME = "wevity"
LABEL = "위비티 공모전"
NEEDS_KEY = False
LIST = "https://www.wevity.com/"
DETAIL = "https://www.wevity.com/?c=find&s=1&gbn=view&ix={}"
TARGETS = {"30": "청소년", "5": "대학생", "32": "제한없음", "4": "일반인"}
ROW = re.compile(r'<div class="tit">\s*<a href="[^"]*ix=(\d+)">(.*?)</a>\s*(?:<div class="sub-tit">(.*?)</div>)?.*?'
                 r'<div class="organ">(.*?)</div>\s*<div class="day">\s*(.*?)<span class="dday ([a-z]+)">(.*?)</span>', re.S)


def fetch():
    seen: dict[str, dict] = {}
    for cidx, target in TARGETS.items():
        for page in range(1, cc.max_pages(NAME) + 1):
            rows = ROW.findall(cc.get(LIST, {"c": "find", "s": 1, "gub": 2, "cidx": cidx, "gp": page}).text)
            live = [r for r in rows if r[5] != "end"]
            if not live:
                break
            for ix, title, sub, org, dday, _cls, _st in live:
                cats = [c.strip() for c in re.sub(r"^\s*분야\s*:", "", cc.clean(sub)).split(",") if c.strip()]
                rec = seen.setdefault(ix, {"title": title, "org": org, "dday": cc.clean(dday), "targets": [], "cats": cats})
                if target not in rec["targets"]:
                    rec["targets"].append(target)
    order = list(TARGETS.values())
    items = []
    for ix, r in seen.items():
        it = cc.make_item(NAME, ix, title=r["title"], host=r["org"], url=DETAIL.format(ix),
                          apply_end=cc.from_dday(r["dday"]), categories=r["cats"],
                          target=sorted(r["targets"], key=order.index))
        if it:
            items.append(it)
    return items
