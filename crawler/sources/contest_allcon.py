"""올콘 (all-con.co.kr) 공모전 목록. Listing facts only (see crawler/contests_common.py).

The list is a JSON endpoint (POST, t=1 = 공모전). Each row carries badges: one or more categories and the
eligibility words (대학생, 일반인, 제한없음...), told apart by TARGET_BADGES. The period is 'yy.mm.dd~yy.mm.dd'.
The host column is cut at about 12 characters ('해양심층수산업 고성진흥…'); when the first host itself is cut,
the detail page's 주최 cell is read (host only, nothing else), so the name matches other sites for de-duplication.
올콘's TLS chain lacks its intermediate certificate, so requests skip verification; robots.txt is still checked.
"""
import re

from .. import contests_common as cc

NAME = "allcon"
LABEL = "올콘 공모전"
NEEDS_KEY = False
API = "https://www.all-con.co.kr/page/ajax.contest_list.php"
DETAIL = "https://www.all-con.co.kr/view/contest/{}"
# Badges that name who may enter (seen 2026-09-27); every other badge is a category ('사진·영상', '문학·학술').
TARGET_BADGES = {"제한없음", "일반인", "대학생", "대학원생", "고등학생", "중학생", "초등학생", "청소년", "주부 및 영유아", "기타"}
HOST_CELL = re.compile(r"class='title_host'>\s*주최\s*</th>\s*<td[^>]*>(.*?)</td>", re.S)


def _full_host(srl: str) -> str:
    cc._prime_robots_unverified(DETAIL.format(srl))
    cc.http._check_robots(DETAIL.format(srl))
    cc._throttle(DETAIL.format(srl))
    try:
        r = cc.http._session.get(DETAIL.format(srl), timeout=30, verify=False)
        m = HOST_CELL.search(r.text)
        return cc.clean(m.group(1)) if m else ""
    except Exception:
        return ""


def fetch():
    items = {}
    for page in range(1, cc.max_pages(NAME) + 1):
        d = cc.post(API, data={"page": page, "t": "1", "sortname": "cl_order", "sortorder": "asc"},
                    headers={"X-Requested-With": "XMLHttpRequest"}, verify=False).json()
        rows = d.get("rows") or []
        rows = list(rows.values()) if isinstance(rows, dict) else rows
        if not rows:
            break
        for v in rows:
            srl = v.get("cl_srl")
            if not srl or "cl_title" not in v or "마감" in cc.clean(v.get("cl_status")):
                continue
            m = re.match(r"(\d\d)\.(\d\d)\.(\d\d)~(\d\d)\.(\d\d)\.(\d\d)", v.get("cl_date") or "")
            start = end = None
            if m:
                g = m.groups()
                start, end = cc.ymd(f"20{g[0]}-{g[1]}-{g[2]}"), cc.ymd(f"20{g[3]}-{g[4]}-{g[5]}")
            badges = [cc.clean(b) for b in re.findall(r"cl_cate\">(.*?)<", v.get("cl_cate") or "")]
            host = cc.clean(v.get("cl_host"))
            if cc.truncated(host.split(",")[0]):
                host = _full_host(srl) or host.rstrip("….")
            targets = [b for b in badges if b in TARGET_BADGES]
            cats = [b for b in badges if b not in TARGET_BADGES]
            it = cc.make_item(NAME, srl, title=v["cl_title"], host=host, url=DETAIL.format(srl),
                              apply_start=start, apply_end=end, categories=cats, target=targets)
            if it:
                items[srl] = it
        if page >= int(d.get("totalPage") or 0):
            break
    return list(items.values())
