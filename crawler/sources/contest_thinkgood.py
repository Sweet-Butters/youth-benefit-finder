"""씽굿 (thinkcontest.com) 공모전 목록. Listing facts only (see crawler/contests_common.py).

JSON list endpoint (POST), 10 rows a page whatever is asked. Sorted by D-day, latest deadline first, so
open contests come first and the walk stops at the first page with nothing still open.
Eligibility is `enter_qualified_nm` ('중학생, 고등학생, 동 연령대 청소년'); `enter_qualified_etc` is the site's
one-line note ('경기도 소재 대학 재학생'), kept as the note (a province in it becomes the region).
"""
import json

from .. import contests_common as cc

NAME = "thinkgood"
LABEL = "씽굿 공모전"
NEEDS_KEY = False
API = "https://www.thinkcontest.com/thinkgood/user/contest/subList.do"
DETAIL = "https://www.thinkcontest.com/thinkgood/user/contest/view.do?contest_pk={}"


def fetch():
    items = {}
    for page in range(1, cc.max_pages(NAME) + 1):
        body = {"recordsPerPage": 10, "currentPageNo": page, "contest_field": "", "host_organ": "",
                "enter_qualified": "", "award_size": "", "searchStatus": "Y", "sidx": "d_day", "sord": "DESC"}
        rows = cc.post(API, data=json.dumps(body), headers={"Content-Type": "application/json"}).json().get("listJsonData") or []
        live = [x for x in rows if x.get("process_nm") != "마감" and x.get("contest_pk")]
        if not live:
            break
        for x in live:
            pk = x["contest_pk"]
            cats = [c.strip() for c in cc.clean(x.get("contest_field_nm")).split(",") if c.strip()]
            it = cc.make_item(NAME, pk, title=x.get("program_nm"), host=x.get("host_company"), url=DETAIL.format(pk),
                              apply_start=cc.ymd(x.get("accept_dt")), apply_end=cc.ymd(x.get("finish_dt")),
                              categories=cats, target=x.get("enter_qualified_nm") or "",
                              note=x.get("enter_qualified_etc") or "")
            if it:
                items[pk] = it
    return list(items.values())
