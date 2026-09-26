import datetime as dt
import re

KST = dt.timezone(dt.timedelta(hours=9))


def today() -> dt.date:
    return dt.datetime.now(KST).date()


def ymd(s: str | None) -> str | None:
    """'20261215', '2026/09/23', '2026.09.23', '2026-09-23' -> '2026-09-23'. Anything else -> None."""
    if not s:
        return None
    m = re.search(r"(20\d\d)[./-]?(\d{1,2})[./-]?(\d{1,2})", str(s))
    if not m:
        return None
    y, mo, d = (int(x) for x in m.groups())
    try:
        return dt.date(y, mo, d).isoformat()
    except ValueError:
        return None


REGION_CODES = {
    "서울": "seoul", "부산": "busan", "대구": "daegu", "인천": "incheon", "광주": "gwangju", "대전": "daejeon",
    "울산": "ulsan", "세종": "sejong", "경기": "gyeonggi", "강원": "gangwon", "충북": "chungbuk", "충청북": "chungbuk",
    "충남": "chungnam", "충청남": "chungnam", "전북": "jeonbuk", "전라북": "jeonbuk", "전남": "jeonnam", "전라남": "jeonnam",
    "경북": "gyeongbuk", "경상북": "gyeongbuk", "경남": "gyeongnam", "경상남": "gyeongnam", "제주": "jeju",
}


def region_code(text: str | None) -> str | None:
    if not text:
        return None
    for k, v in REGION_CODES.items():
        if k in text:
            return v
    return None
