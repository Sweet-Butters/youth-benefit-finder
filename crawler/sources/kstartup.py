"""K-Startup 사업공고 (창업진흥원), notices open to 청소년·학생·청년 only.

Two ways in, tried in order:
1. The data.go.kr API (dataset 15125364, B552735/kisedKstartupService01/getAnnouncementInformation01),
   which has 신청 대상 (aply_trgt), 대상 연령 (biz_trgt_age) and all ongoing notices. On 2026-09-27
   our key got SERVICE_KEY_IS_NOT_REGISTERED: someone must apply on
   https://www.data.go.kr/data/15125364/openapi.do (development use is auto-approved). This path
   follows the swagger on that page and has not been run yet.
2. Until then, the public list page. Anonymous visitors only get page 1 (paging and search need the
   site's session; GET parameters are ignored), so this sees the newest ~25 notices a day, and
   earlier ones stay in our results through merge until their deadline. Each notice's own page
   (plain GET, robots.txt allows /web/contents/) has 대상, 대상연령, 지역 and 접수기간.

Kept: the title names youth, or 대상 lists 청소년/대학생/학생, or 대상연령 includes 만 20세 미만 or stops
at 39; and the title does not say the applicant is a company or an operating institution
(config/startup-youth.json, shared with bizinfo.py). 대상연령 becomes age_min/age_max for youth.judge.
"""
import html
import re
import time

from .. import http
from ..model import Item
from ..util import regions_from_text, today, ymd
from .bizinfo import rules

NAME = "kstartup"
LABEL = "K-Startup 창업 지원 (청소년·청년)"
NEEDS_KEY = False   # the public page works without a key; the API is used when the key is registered
API = "https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01"
LIST = "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do"
VIEW = LIST + "?schM=view&pbancSn={}"
TAGS = ["startup", "field:business-sales"]
STUDENT = re.compile(r"청소년|대학생|학생")
PAUSE = 1.0   # seconds between detail pages


def _clean(s) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", str(s or ""))).split())


def _ages(text: str) -> tuple[int | None, int | None]:
    """"만 20세 미만, 만 20세 이상 ~ 만 39세 이하" -> (None, 39); any 40세 이상 -> no upper bound."""
    if not text:
        return None, None
    lows, highs = [], []
    for m in re.finditer(r"만\s*(\d+)\s*세\s*(미만|이상|이하)(?:\s*~\s*만\s*(\d+)\s*세\s*(이하|미만))?", text):
        a, kind, b, kind2 = m.group(1), m.group(2), m.group(3), m.group(4)
        if kind == "미만":
            lows.append(0); highs.append(int(a) - 1)
        elif b:
            lows.append(int(a)); highs.append(int(b) - (1 if kind2 == "미만" else 0))
        elif kind == "이상":
            lows.append(int(a)); highs.append(200)
        else:
            lows.append(0); highs.append(int(a))
    if not lows:
        return None, None
    lo, hi = min(lows), max(highs)
    return (lo or None), (None if hi >= 200 else hi)


def _open_to_youth(title: str, target: str, ages: str, r) -> bool:
    if r["company"].search(title):
        return False
    lo, hi = _ages(ages)
    return bool(r["youth"].search(title) or STUDENT.search(target) or "20세 미만" in ages
                or (hi is not None and hi <= 39))


def _item(sn: str, title: str, provider: str, url: str, start, end, region_text: str,
          target: str, ages: str, extra: dict) -> Item:
    lo, hi = _ages(ages)
    # "전남광주통합특별시" alone covers two codes; regions_from_text keeps both.
    regions = ["all"] if "전국" in region_text else regions_from_text(region_text)
    return Item(
        source=NAME,
        source_id=sn,
        type="support",
        title=title[:100],
        provider=provider[:60] or "창업진흥원 (K-Startup)",
        url=url,
        summary=f"{provider or 'K-Startup'}의 창업 지원 공고예요. 자격과 지원 내용은 공고문에서 확인해요.",
        apply_start=start,
        apply_end=end,
        regions=regions,
        age_min=lo,
        age_max=hi,
        target_text=" ".join(x for x in (f"대상: {target}." if target else "",
                                         f"대상연령: {ages}." if ages else "",
                                         extra.get("apply_target", "")) if x)[:300],
        tags=list(TAGS),
        extra=extra,
    )


def _from_api(r) -> list[Item]:
    items: list[Item] = []
    cutoff = today().isoformat()
    for page in range(1, 20):
        body = http.get(API, {"page": page, "perPage": 500, "returnType": "json",
                              "cond[rcrt_prgs_yn::EQ]": "Y"}, api_key=True, retries=1).json()
        rows = body.get("data") or []
        for x in rows:
            title = _clean(x.get("biz_pbanc_nm"))
            target, ages = _clean(x.get("aply_trgt")), _clean(x.get("biz_trgt_age"))
            end = ymd(x.get("pbanc_rcpt_end_dt"))
            if not title or (end and end < cutoff) or not _open_to_youth(title, target, ages, r):
                continue
            sn = str(x.get("pbanc_sn") or "")
            url = next((u for u in (x.get("detl_pg_url"), x.get("biz_aply_url")) if str(u or "").startswith("http")),
                       VIEW.format(sn))
            extra = {"pbancSn": sn, "field": _clean(x.get("supt_biz_clsfc")), "apply_target": _clean(x.get("aply_trgt_ctnt"))[:200],
                     "founding_period": _clean(x.get("biz_enyy"))}
            items.append(_item(sn, title, _clean(x.get("pbanc_ntrp_nm")) or _clean(x.get("sprv_inst")), url,
                               ymd(x.get("pbanc_rcpt_bgng_dt")), end, _clean(x.get("supt_regin")), target, ages,
                               {k: v for k, v in extra.items() if v}))
        if not rows or page * 500 >= int(body.get("totalCount") or 0):
            break
    return items


def _fields(page: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in re.finditer(r'<p class="tit">\s*(.*?)\s*</p>\s*<p class="txt"[^>]*>(.*?)</p>', page, re.S):
        out.setdefault(_clean(m.group(1)), _clean(m.group(2)))
    return out


def _from_page(r) -> list[Item]:
    listing = http.get(LIST).text
    ids = list(dict.fromkeys(re.findall(r"go_view\((\d+)\)", listing)))
    cutoff = today().isoformat()
    items: list[Item] = []
    for sn in ids:
        time.sleep(PAUSE)
        page = http.get(VIEW.format(sn)).text
        f = _fields(page)
        h3 = re.search(r"<h3[^>]*>(.*?)</h3>", page, re.S)
        title = _clean(h3.group(1)) if h3 else ""
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", f.get("접수기간", ""))
        start, end = (ymd(dates[0]) if dates else None), (ymd(dates[1]) if len(dates) > 1 else None)
        target, ages = f.get("대상", ""), f.get("대상연령", "")
        if not title or (end and end < cutoff) or not _open_to_youth(title, target, ages, r):
            continue
        extra = {"pbancSn": sn, "field": f.get("지원분야", ""), "apply_target": f.get("신청대상", "")[:200],
                 "founding_period": f.get("창업업력", "")}
        items.append(_item(sn, title, f.get("주관기관명", ""), VIEW.format(sn), start, end, f.get("지역", ""),
                           target, ages, {k: v for k, v in extra.items() if v}))
    return items


def fetch() -> list[Item]:
    r = rules()
    try:
        return _from_api(r)
    except Exception:   # key not registered for this dataset yet, or no key: use the public page
        return _from_page(r)
