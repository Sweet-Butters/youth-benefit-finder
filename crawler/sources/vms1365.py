"""1365 자원봉사포털 봉사 모집 (행정안전부 봉사참여정보서비스, data.go.kr 15157582).

What the API gives (checked 2026-09-27):
- getVltrSearchWordList with yngbgsPosblAt=Y lists only recruitments whose notice has not ended
  (noticeEndde >= today), sorted by that end date: about 3,900 rows, so 4 calls at numOfRows=1000.
  progrmSttusSe: 1 모집대기, 2 모집중, 3 모집완료 (full). We keep 1 and 2.
- Date filters (progrmBgnde ...) are broken on the legacy host (SQL error), so we filter here.
- Each row carries its own 1365 detail link (url); DETAIL is the same page when it is missing.

Endpoints: the legacy host openapi.1365.go.kr answers with our data.go.kr key. The newer gateway
apis.data.go.kr/1741000/volunteerPartcptnService (dataset 15157582, "_GW", opened 2026-03) says
SERVICE_KEY_IS_NOT_REGISTERED until someone applies for it on
https://www.data.go.kr/data/15157582/openapi.do (development use is auto-approved). Both return the
same XML, so we try the legacy host first and the gateway second.

These are programs that accept youth volunteers (청소년가능); most also accept adults. They are different programs from
DOVOL (volunteer.py), so there is no dedupe between the two.
"""
import xml.etree.ElementTree as ET

from .. import http
from ..model import Item
from ..util import region_code, region_from_text, today, ymd

NAME = "vms1365"
LABEL = "1365 자원봉사 (청소년 가능)"
NEEDS_KEY = True
ENDPOINTS = [
    "http://openapi.1365.go.kr/openapi/service/rest/VolunteerPartcptnService/getVltrSearchWordList",
    "https://apis.data.go.kr/1741000/volunteerPartcptnService/getVltrSearchWordList",
]
DETAIL = "https://www.1365.go.kr/vols/P9210/partcptn/timeCptn.do?type=show&progrmRegistNo={}"
ROWS = 1000
OPEN = {"1", "2"}          # 모집대기, 모집중
STATUS = {"1": "모집대기", "2": "모집중", "3": "모집완료"}
# 행정기관 시도 codes as the API sends them (강원·전북 keep their old codes).
SIDO_CODE = {
    "6110000": "서울", "6260000": "부산", "6270000": "대구", "6280000": "인천", "6290000": "광주",
    "6300000": "대전", "6310000": "울산", "5690000": "세종", "6410000": "경기", "6420000": "강원",
    "6530000": "강원", "6430000": "충북", "6440000": "충남", "6450000": "전북", "6540000": "전북",
    "6460000": "전남", "6470000": "경북", "6480000": "경남", "6500000": "제주",
}


def _page(url: str, page: int) -> tuple[list[dict], int]:
    text = http.get(url, {"pageNo": page, "numOfRows": ROWS, "yngbgsPosblAt": "Y"},
                    api_key=True, timeout=60).text
    root = ET.fromstring(text)
    code = root.findtext(".//resultCode")
    if code != "00":
        msg = root.findtext(".//resultMsg") or root.findtext(".//returnAuthMsg") or root.findtext(".//errMsg")
        raise RuntimeError(f"vms1365 error {code} {msg}")
    rows = [{c.tag: (c.text or "").strip() for c in it} for it in root.iter("item")]
    return rows, int(root.findtext(".//totalCount") or 0)


def _rows() -> list[dict]:
    errors = []
    for url in ENDPOINTS:
        try:
            rows, total = _page(url, 1)
        except Exception as e:  # try the other host
            errors.append(str(e)[:200])
            continue
        for page in range(2, 30):
            if len(rows) >= total:
                break
            got, _ = _page(url, page)
            if not got:
                break
            rows += got
        return rows
    raise RuntimeError("vms1365: no endpoint answered: " + " | ".join(errors))


def _clean(s) -> str:
    return " ".join(str(s or "").split())


def _hours(a: str, b: str) -> str:
    return f"{int(a)}시~{int(b)}시" if a.isdigit() and b.isdigit() else ""


def fetch() -> list[Item]:
    cutoff = today().isoformat()
    items: list[Item] = []
    seen: set[str] = set()
    for row in _rows():
        no = row.get("progrmRegistNo", "")
        apply_end = ymd(row.get("noticeEndde"))
        if (not no or no in seen or row.get("yngbgsPosblAt") != "Y" or row.get("progrmSttusSe") not in OPEN
                or not apply_end or apply_end < cutoff):
            continue
        seen.add(no)
        title = _clean(row.get("progrmSj"))[:80]
        provider = _clean(row.get("nanmmbyNm"))[:60] or "1365 자원봉사포털"
        place = _clean(row.get("actPlace"))
        field = _clean(row.get("srvcClCode"))
        region = region_code(SIDO_CODE.get(row.get("sidoCd", ""))) or region_from_text(place)
        url = row.get("url", "")
        if not url.startswith(("http://", "https://")):
            url = DETAIL.format(no)
        hours = _hours(row.get("actBeginTm", ""), row.get("actEndTm", ""))
        adult_ok = row.get("adultPosblAt") == "Y"
        summary = f"{provider}에서 모집하는 {field or '자원'} 봉사예요."
        if hours:
            summary += f" 활동 시간은 {hours}이에요."
        extra = {"progrmRegistNo": no, "status": STATUS.get(row.get("progrmSttusSe", ""), row.get("progrmSttusSe")),
                 "adult_ok": adult_ok,
                 "how_to_apply": "1365 자원봉사포털에서 로그인한 뒤 신청해요. 청소년은 보호자 동의가 필요할 수 있어요."}
        if place:
            extra["place"] = place[:60]
        if hours:
            extra["hours"] = hours
        items.append(Item(
            source=NAME,
            source_id=no,
            type="experience",
            title=title,
            provider=provider,
            url=url,
            summary=summary,
            apply_start=ymd(row.get("noticeBgnde")),
            apply_end=apply_end,
            event_start=ymd(row.get("progrmBgnde")),
            event_end=ymd(row.get("progrmEndde")),
            regions=[region] if region else [],
            # The API flags who may volunteer; titles name who is served ("어르신 말벗"), which the
            # text rules in youth.py would read as adult-only. Adults and youth -> open_to_all;
            # youth only -> 1365's 청소년 means under 19.
            age_max=None if adult_ok else 18,
            target_text="청소년 가능 (1365 청소년가능 표시)" + (", 성인 가능" if adult_ok else ""),
            tags=["volunteer"] + ([f"volunteer:{field}"] if field else []) + (["open_to_all"] if adult_ok else []),
            extra=extra,
        ))
    return items
