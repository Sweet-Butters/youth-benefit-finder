"""청소년활동 인증프로그램 (성평등가족부·한국청소년활동진흥원, data.go.kr 15069276).

API: https://apis.data.go.kr/1383000/YouthActivInfoCertiSrvc2 (XML only, no JSON option).
- getCertiProgrmList: pageNo, numOfRows (500 works), sido, sigungu, pgm, org, sdate/edate (YYYYMMDD,
  활동시작일/종료일 window). The response <sdate> is the *registration* date, not the activity date.
- getCertiActiDateList: key1=<nums> -> every activity session (sdate/edate/procNo) of one program.
- getCertiProgrmInfo: key1=<nums> -> detail text, contact (not used: it adds a call per item and the
  prose is not ours to copy).

We only ask for programs with a session in the next WINDOW_DAYS days, once per 시도 so each item gets a
region (the list has no region field). Then one date call per program gives the real session dates.
About 17 + ~200 calls a day; the dev quota is 10,000.
"""
import datetime as dt
import xml.etree.ElementTree as ET

from .. import http
from ..model import Item
from ..util import today, ymd

NAME = "certi"
LABEL = "청소년활동 인증프로그램"
NEEDS_KEY = True
BASE = "https://apis.data.go.kr/1383000/YouthActivInfoCertiSrvc2"
PAGE_URL = "https://www.youth.go.kr/"   # no stable per-program link can be built from the API id
WINDOW_DAYS = 90
PAGE_SIZE = 500

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


def fetch() -> list[Item]:
    start = today()
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

    items: list[Item] = []
    for nums, (row, regions) in found.items():
        sessions = []
        for d in _rows("getCertiActiDateList", {"key1": nums}):
            s, e = ymd(d.get("sdate")), ymd(d.get("edate"))
            if s and (e or s) >= start.isoformat():
                sessions.append((s, e or s))
        sessions = sorted(set(sessions))
        if not sessions:
            continue
        lo, hi, target_text = _ages(row.get("target", ""))
        price = (row.get("price") or "").replace(",", "")
        cost = "" if not price else "무료" if price == "0" else f"{int(price):,}원" if price.isdigit() else price
        items.append(Item(
            source=NAME,
            source_id=nums,
            type="experience",
            title=(row.get("pgmNm") or "").strip(),
            provider=(row.get("organNm") or "").strip(),
            url=PAGE_URL,
            summary="국가가 인증한 청소년 수련활동이에요. 신청 방법은 e청소년이나 운영 기관에서 확인해요.",
            event_start=sessions[0][0], event_end=sessions[0][1],
            regions=regions,
            age_min=lo, age_max=hi,
            target_text=target_text,
            cost_text=cost,
            tags=["certified"],
            extra={"certNo": nums, "registered": ymd(row.get("sdate")),
                   "sessions": [f"{s}~{e}" if e != s else s for s, e in sessions]},
        ))
    return items
