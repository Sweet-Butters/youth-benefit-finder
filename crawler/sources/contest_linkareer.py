"""링커리어 (linkareer.com) 공모전 목록. Listing facts only (see crawler/contests_common.py).

Server-rendered Next.js pages carry an Apollo cache in __NEXT_DATA__ (title, organizationName, recruitCloseAt).
The list shows no eligibility, but it filters by target (filterBy_targetIDs: 1 청소년, 2 대학생, 3 직장인/일반인,
4 대상 제한 없음; checked against detail pages 2026-09-27), so each target list is walked and a contest's target is
the set of lists it appears in. Open contests only (the list's status filter). No category in the list.
"""
import json
import re

from .. import contests_common as cc

NAME = "linkareer"
LABEL = "링커리어 공모전"
NEEDS_KEY = False
LIST = "https://linkareer.com/list/contest"
DETAIL = "https://linkareer.com/activity/{}"
TARGETS = {"1": "청소년", "2": "대학생", "3": "직장인/일반인", "4": "대상 제한 없음"}


def _apollo(page_html: str) -> dict:
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', page_html, re.S)
    if not m:
        return {}
    return json.loads(m.group(1)).get("props", {}).get("pageProps", {}).get("__APOLLO_STATE__", {}) or {}


def fetch():
    seen: dict[str, dict] = {}
    for tid, target in TARGETS.items():
        for page in range(1, cc.max_pages(NAME) + 1):
            st = _apollo(cc.get(LIST, {"filterBy_targetIDs": tid, "filterType": "TARGET", "orderBy_direction": "DESC",
                                       "orderBy_field": "CREATED_AT", "page": page}).text)
            acts = [v for k, v in st.items() if k.startswith("Activity:") and v.get("id")]
            if not acts:
                break
            for a in acts:
                rec = seen.setdefault(a["id"], {"a": a, "targets": []})
                if target not in rec["targets"]:
                    rec["targets"].append(target)
    order = list(TARGETS.values())
    items = []
    for aid, r in seen.items():
        a = r["a"]
        it = cc.make_item(NAME, aid, title=a.get("title"), host=a.get("organizationName"), url=DETAIL.format(aid),
                          apply_end=cc.from_epoch_ms(a.get("recruitCloseAt")),
                          target=sorted(r["targets"], key=order.index))
        if it:
            items.append(it)
    return items
