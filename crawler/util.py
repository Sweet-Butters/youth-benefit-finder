import datetime as dt
import json
import re
from pathlib import Path

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


# ---------------------------------------------------------------------------
# Place names in free text -> province codes (config/sigungu.json for 시·군·구).
# A wrong province is worse than none, so anything ambiguous stays unknown.

_SIGUNGU_FILE = Path(__file__).resolve().parents[1] / "config" / "sigungu.json"

# Province-level names, each a set of the codes it may mean. 광주 alone reads as 광주광역시;
# the 2026 전남광주통합특별시 covers both and a district after it decides which.
_PROVINCES: dict[str, set[str]] = {
    **{n: {"seoul"} for n in ("서울특별시", "서울시", "서울")},
    **{n: {"busan"} for n in ("부산광역시", "부산시", "부산")},
    **{n: {"daegu"} for n in ("대구광역시", "대구시", "대구")},
    **{n: {"incheon"} for n in ("인천광역시", "인천시", "인천")},
    **{n: {"gwangju"} for n in ("광주광역시", "광주")},
    **{n: {"daejeon"} for n in ("대전광역시", "대전시", "대전")},
    **{n: {"ulsan"} for n in ("울산광역시", "울산시", "울산")},
    **{n: {"sejong"} for n in ("세종특별자치시", "세종시", "세종")},
    **{n: {"gyeonggi"} for n in ("경기도", "경기")},
    **{n: {"gangwon"} for n in ("강원특별자치도", "강원도", "강원")},
    **{n: {"chungbuk"} for n in ("충청북도", "충북")},
    **{n: {"chungnam"} for n in ("충청남도", "충남")},
    **{n: {"jeonbuk"} for n in ("전북특별자치도", "전라북도", "전북")},
    **{n: {"jeonnam"} for n in ("전라남도", "전남")},
    **{n: {"gyeongbuk"} for n in ("경상북도", "경북")},
    **{n: {"gyeongnam"} for n in ("경상남도", "경남")},
    **{n: {"jeju"} for n in ("제주특별자치도", "제주도", "제주")},
    **{n: {"gwangju", "jeonnam"} for n in ("전남광주통합특별시", "광주전남통합특별시", "전남광주", "광주전남")},
}
_WHOLE = {"전남광주통합특별시", "광주전남통합특별시", "전남광주", "광주전남"}   # alone: every code they cover
_names_cache: dict[str, set[str]] | None = None
_pattern_cache: re.Pattern | None = None


def _names() -> tuple[dict[str, set[str]], re.Pattern]:
    global _names_cache, _pattern_cache
    if _names_cache is None:
        data = json.loads(_SIGUNGU_FILE.read_text(encoding="utf-8"))["names"]
        names = {k: ({v} if isinstance(v, str) else set(v)) for k, v in data.items()}
        for k, v in _PROVINCES.items():
            names[k] = set(v)
        _names_cache = names
        alts = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
        # "서울대", "부산대학교", "세종대왕" name a school or a person, not a place.
        _pattern_cache = re.compile(f"({alts})(?!대(?:학|왕|회|[^가-힣]|$))")
    return _names_cache, _pattern_cache


def regions_from_text(text: str | None) -> list[str]:
    """Province codes named in free text, in order; [] when none or ambiguous.

    A name counts only at a word start (so 강남구 never yields 남구) or right after another place
    name ("수원시장안구"). Names written next to each other narrow each other: "대구 중구" -> daegu,
    "전남광주통합특별시 서구" -> gwangju, "경기도 광주시" -> gyeonggi. A lone 중구, 고성군 or 광주시 is
    ambiguous and adds nothing.
    """
    if not text:
        return []
    names, pat = _names()
    groups: list[tuple[set[str], int, str]] = []   # (candidates, end, first name)
    pos = 0
    while True:
        m = pat.search(text, pos)
        if not m:
            break
        s, e = m.span()
        prev = text[s - 1] if s else ""
        chained = bool(groups) and not text[groups[-1][1]:s].strip()
        if prev and "가" <= prev <= "힣" and not (chained and groups[-1][1] == s):
            pos = s + 1
            continue
        cands = names[m.group(1)]
        if chained and groups[-1][0] & cands:
            groups[-1] = (groups[-1][0] & cands, e, groups[-1][2] + " " + m.group(1))
        elif chained and groups[-1][1] == s:
            pass   # glued to a place it cannot belong to ("서울제주도민회"): part of a longer name
        else:
            groups.append((set(cands), e, m.group(1)))
        pos = e
    out: list[str] = []
    for cands, _, first in groups:
        picked = sorted(cands) if len(cands) == 1 or first in _WHOLE else []
        out += [c for c in picked if c not in out]
    return out


def region_from_text(text: str | None) -> str | None:
    """The one province a text names, or None when it names none, several, or is ambiguous."""
    codes = regions_from_text(text)
    return codes[0] if len(codes) == 1 else None


def _self_check() -> None:
    cases = {
        "홍천군에 주민등록": ["gangwon"],
        "당진발전본부장학회": ["chungnam"],
        "양천구 거주 학생": ["seoul"],
        "(재)광양시장학회": ["jeonnam"],
        "강남구에 주민등록": ["seoul"],            # not 남구
        "중구에 1년 이상 거주": [],                 # 서울·부산·대구·… 모두 있음
        "대구광역시 중구 거주": ["daegu"],
        "울산 동구": ["ulsan"],
        "강서구 거주": [],                          # 서울·부산
        "부산광역시 강서구": ["busan"],
        "(재)전남광주통합특별시 서구 장학재단": ["gwangju"],
        "전남광주통합특별시 목포시": ["jeonnam"],
        "전남광주통합특별시에 주소": ["gwangju", "jeonnam"],
        "광주광역시 거주": ["gwangju"],
        "광주시청": [],                             # 경기 광주시 or 광주광역시
        "경기도 광주시 거주": ["gyeonggi"],
        "고성군 관내": [],                          # 강원·경남
        "강원도 고성군": ["gangwon"],
        "강원특별자치도 거주": ["gangwon"],
        "전라북도 전주시": ["jeonbuk"],
        "전북특별자치도": ["jeonbuk"],
        "수원시장안구": ["gyeonggi"],
        "청주시흥덕구 거주": ["chungbuk"],
        "서울대학교 재학생": [],
        "세종대왕 장학": [],
        "군위군": ["daegu"],
        "서울 또는 경기 거주": ["seoul", "gyeonggi"],
        "관내 거주": [],
        "예산 소진 시": [],                         # 예산군 short form is not a place here
        "영광군민": ["jeonnam"],
        "고령자": [],
        "광주전남통합특별시 소재 대학": ["gwangju", "jeonnam"],
        "서울제주도민회": ["seoul"],
        "경기대회 입상자": [],
    }
    bad = [(t, regions_from_text(t), want) for t, want in cases.items() if regions_from_text(t) != want]
    for t, got, want in bad:
        print(f"FAIL {t!r}: got {got}, want {want}")
    assert region_from_text("대구 달서구") == "daegu" and region_from_text("서울 또는 경기") is None
    print(f"{len(cases) - len(bad)}/{len(cases)} region cases pass")
    if bad:
        raise SystemExit(1)


if __name__ == "__main__":
    _self_check()
