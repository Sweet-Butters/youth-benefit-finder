"""청소년활동 인증프로그램 (성평등가족부·한국청소년활동진흥원, data.go.kr 15069276).

API: https://apis.data.go.kr/1383000/YouthActivInfoCertiSrvc2 (XML only, no JSON option).
- getCertiProgrmList: pageNo, numOfRows (500 works), sido, sigungu, pgm, org, sdate/edate (YYYYMMDD,
  활동시작일/종료일 window). The response <sdate> is the *registration* date, not the activity date.
- getCertiActiDateList: key1=<nums> -> every activity session (sdate/edate/procNo) of one program.
- getCertiProgrmInfo: key1=<nums> -> info2 (활동 내용 list), tel, email, managerNm, no URL or site key.

We only ask for programs with a session in the next WINDOW_DAYS days, once per 시도 so each item gets a
region (the list has no region field). Then one date call per program gives the real session dates.

Per-program page on e청소년 (checked 2026-09-27): the detail page is a plain GET,
  /youth/act/actSearch/actSearchDtl.yt?kFcltySn=11&kCrtfcSn=13026&kSnOne=13026&kProgrmseCode=001003&kSnTwo=0
but its keys are the site's own (kCrtfcSn is not the number in nums), so they cannot be built from the
API. The site's search does accept the certification number:
  /youth/act/actSearch/allActSearchLst.yt?sCrtfc=Y&sCrtfcText=<nums>&sSttemntText=&curMenuSn=334
(without the empty sSttemntText the site answers 500). For each *new* program we read that search page
once, take the fnDtl(...) keys of the row with the same title and link the detail page; if that fails,
the search URL itself is the link (it lists exactly that program).

Detail text, contact and the page keys are cached per nums in data/collected/certi_cache.json, so a daily
run costs 16 list calls + one date call per program (~130) + one info call per program not seen before.
The cache holds no personal data: managerNm (a staff name) and email are not stored.
"""
import datetime as dt
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

from .. import http
from ..model import Item
from ..util import today, ymd

NAME = "certi"
LABEL = "청소년활동 인증프로그램"
NEEDS_KEY = True
BASE = "https://apis.data.go.kr/1383000/YouthActivInfoCertiSrvc2"
SITE = "https://www.youth.go.kr/youth/act/actSearch"
WINDOW_DAYS = 90
PAGE_SIZE = 500
CACHE = Path(__file__).resolve().parents[2] / "data" / "collected" / "certi_cache.json"
RECHECK_DAYS = 7      # a program whose page was not found on the site is looked up again after this
DROP_DAYS = 180       # cache entries not seen for this long are removed

# `sido` is a substring match on the API side. 광주·전남 are one value (전남광주통합특별시);
# 충남/충북/경남/경북 only match the full names.
SIDO = [
    ("서울", ["seoul"]), ("부산", ["busan"]), ("대구", ["daegu"]), ("인천", ["incheon"]),
    ("전남광주", ["gwangju", "jeonnam"]), ("대전", ["daejeon"]), ("울산", ["ulsan"]), ("세종", ["sejong"]),
    ("경기", ["gyeonggi"]), ("강원", ["gangwon"]), ("충청북도", ["chungbuk"]), ("충청남도", ["chungnam"]),
    ("전북", ["jeonbuk"]), ("경상북도", ["gyeongbuk"]), ("경상남도", ["gyeongnam"]), ("제주", ["jeju"]),
]

# 참가대상 "초(10명)중(5명)고(20명)" -> ages
LEVEL_AGES = {"초": (8, 13), "중": (14, 16), "고": (17, 19), "대": (20, 24)}
LEVEL_NAMES = {"초": "초등학생", "중": "중학생", "고": "고등학생", "대": "대학생"}
DTL_KEYS = ("kFcltySn", "kCrtfcSn", "kSnOne", "kProgrmseCode", "kSnTwo")
FN_DTL = re.compile(r"fnDtl\(([^)]*)\);return false;\">\s*([^<]*?)\s*<")


def _call(op: str, params: dict) -> ET.Element:
    root = ET.fromstring(http.get(f"{BASE}/{op}", params, api_key=True).content)
    code = root.findtext(".//resultCode")
    if code != "00":
        raise RuntimeError(f"certi {op} error {code} {root.findtext('.//resultMsg')}")
    return root


def _rows(op: str, params: dict) -> list[dict]:
    rows: list[dict] = []
    for page in range(1, 20):
        root = _call(op, {"pageNo": page, "numOfRows": PAGE_SIZE, **params})
        got = [{c.tag: (c.text or "").strip() for c in it} for it in root.iter("item")]
        rows += got
        if not got or len(rows) >= int(root.findtext(".//totalCount") or 0):
            break
    return rows


def _ages(target: str) -> tuple[int | None, int | None, str]:
    levels = [k for k in LEVEL_AGES if f"{k}(" in target]
    if not levels:
        return None, None, target
    lo = min(LEVEL_AGES[k][0] for k in levels)
    hi = max(LEVEL_AGES[k][1] for k in levels)
    return lo, hi, ", ".join(LEVEL_NAMES[k] for k in levels) + f" ({target})"


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def search_url(nums: str) -> str:
    q = urllib.parse.urlencode({"sCrtfc": "Y", "sCrtfcText": nums, "sSttemntText": "", "curMenuSn": "334"})
    return f"{SITE}/allActSearchLst.yt?{q}"


def detail_url(keys: dict) -> str:
    return f"{SITE}/actSearchDtl.yt?" + urllib.parse.urlencode({k: keys[k] for k in DTL_KEYS})


def _lookup_page(nums: str, title: str) -> dict | None:
    """The site's detail keys for one program, from its certification-number search. None if not found."""
    html = http.get(search_url(nums), timeout=30).text
    rows = []
    for args, name in FN_DTL.findall(html):
        vals = [a.strip().strip("'") for a in args.split(",")]
        if len(vals) >= 5 and vals[1]:
            rows.append((dict(zip(DTL_KEYS, [vals[0], vals[1], vals[2], vals[3], vals[4]])), name))
    same = [k for k, name in rows if name and _norm(name) == _norm(title)]
    distinct = {tuple(k.values()) for k, _ in rows}
    if same:
        return same[0]
    if len(distinct) == 1:
        return rows[0][0]
    return None


def _load_cache() -> dict:
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_cache(cache: dict) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(dict(sorted(cache.items())), ensure_ascii=False, indent=1)
    CACHE.write_text(text + "\n", encoding="utf-8")


def _details(nums: str, title: str, cache: dict, run: str, stats: dict) -> dict:
    """Cached detail for one program: {"info": {...}, "page": {...} | None, "page_checked": date, "seen": date}."""
    c = cache.setdefault(nums, {})
    if "info" not in c:
        try:
            got = _rows("getCertiProgrmInfo", {"key1": nums})
            row = got[0] if got else {}
            c["info"] = {k: row.get(k, "") for k in ("info2", "tel") if row.get(k, "") not in ("", "-")}
            stats["info_calls"] += 1
        except Exception:     # one bad detail call must not drop the program; retried next run
            stats["info_failed"] += 1
    old = c.get("page_checked", "")
    stale = not old or (c.get("page") is None and old < (dt.date.fromisoformat(run) - dt.timedelta(days=RECHECK_DAYS)).isoformat())
    if "page" not in c or stale:
        try:
            c["page"] = _lookup_page(nums, title)
            c["page_checked"] = run
            stats["page_lookups"] += 1
        except Exception:
            stats["page_failed"] += 1
    c["seen"] = run
    return c


def _phone(tel: str) -> str:
    """'0220390957' -> '02-2039-0957'; anything already formatted or odd is left alone."""
    d = re.sub(r"\D", "", tel)
    if "-" in tel or not 9 <= len(d) <= 11:
        return tel.strip()
    if d.startswith("02"):
        return f"02-{d[2:-4]}-{d[-4:]}"
    return f"{d[:3]}-{d[3:-4]}-{d[-4:]}"


def _activities(text: str) -> tuple[str, str]:
    """(short list for the summary or '', cleaned text for extra.activities).

    Only a plain comma list ("입소식, 암벽, 골프, 펜싱") goes into our summary; longer prose from the
    organiser stays in extra, cut short, with bullets and line breaks flattened.
    """
    lines = [re.sub(r"^[\s\-•·○●◎▶?①-⑳\d.)]+", "", ln).strip() for ln in re.split(r"[\r\n]+", text)]
    flat = " ".join(" · ".join(ln for ln in lines if ln).split())
    short = ""
    if "\n" not in text and "," in flat and len(flat) <= 80 and not re.search(r"다\.?$|[:：]", flat):
        short = flat.rstrip(" .")
    return short, (flat[:200].rsplit(" ", 1)[0] + " …") if len(flat) > 200 else flat


def fetch() -> list[Item]:
    start = today()
    run = start.isoformat()
    end = start + dt.timedelta(days=WINDOW_DAYS)
    window = {"sdate": start.strftime("%Y%m%d"), "edate": end.strftime("%Y%m%d")}

    found: dict[str, tuple[dict, list[str]]] = {}
    for sido, regions in SIDO:
        for row in _rows("getCertiProgrmList", {"sido": sido, **window}):
            nums = row.get("nums")
            if nums and nums not in found:
                # 전남광주 is one sido value: 광주 (incl. 광산구) by name, every other 시·군 is 전남
                reg = regions
                if len(regions) > 1:
                    org = row.get("organNm") or ""
                    reg = ["gwangju"] if ("광주" in org or "광산" in org) else ["jeonnam"]
                found[nums] = (row, reg)

    cache = _load_cache()
    stats = {"info_calls": 0, "info_failed": 0, "page_lookups": 0, "page_failed": 0}
    items: list[Item] = []
    try:
        for nums, (row, regions) in found.items():
            sessions = []
            for d in _rows("getCertiActiDateList", {"key1": nums}):
                s, e = ymd(d.get("sdate")), ymd(d.get("edate"))
                if s and (e or s) >= run:
                    sessions.append((s, e or s))
            sessions = sorted(set(sessions))
            if not sessions:
                continue
            title = (row.get("pgmNm") or "").strip()
            det = _details(nums, title, cache, run, stats)
            info = det.get("info") or {}
            lo, hi, target_text = _ages(row.get("target", ""))
            price = (row.get("price") or "").replace(",", "")
            cost = "" if not price else "무료" if price == "0" else f"{int(price):,}원" if price.isdigit() else price
            short, activities = _activities(info.get("info2", ""))
            summary = "국가가 인증한 청소년 수련활동이에요."
            summary += f" 주요 활동: {short}." if short else " 활동 내용과 회차는 e청소년 페이지에서 볼 수 있어요."
            extra = {"certNo": nums, "registered": ymd(row.get("sdate")),
                     "sessions": [f"{s}~{e}" if e != s else s for s, e in sessions],
                     "how_to_apply": "e청소년 활동 페이지에서 회차를 골라 신청하거나, 운영 기관에 전화로 문의해요."}
            if info.get("tel"):
                extra["contact"] = f"{(row.get('organNm') or '').strip()} {_phone(info['tel'])}".strip()
            if activities:
                extra["activities"] = activities
            items.append(Item(
                source=NAME,
                source_id=nums,
                type="experience",
                title=title,
                provider=(row.get("organNm") or "").strip(),
                url=detail_url(det["page"]) if det.get("page") else search_url(nums),
                summary=summary,
                event_start=sessions[0][0], event_end=sessions[0][1],
                regions=regions,
                age_min=lo, age_max=hi,
                target_text=target_text,
                cost_text=cost,
                tags=["certified"],
                extra=extra,
            ))
    finally:
        # keep what was learned even if a later call fails; forget programs gone for half a year
        drop = (start - dt.timedelta(days=DROP_DAYS)).isoformat()
        _save_cache({k: v for k, v in cache.items() if v.get("seen", run) >= drop})
    print(f"certi: {len(found)} programs, {stats}")
    return items
