"""청소년 자원봉사활동 프로그램 (한국청소년활동진흥원 DOVOL, data.go.kr 15156325, B552713/svc003).

What the API allows (checked 2026-09 against the swagger on the dataset page):
- Required: pageNo, numOfRows, returnType=json, actvCtpvNm (활동시도명, partial match: '서울' finds
  '서울특별시'). Optional filters are only actvSggNm and prgrmNm (partial match). Any other
  parameter is rejected, so there is no date or status filter.
- Rows are sorted by program name and go back to 2008 (Seoul alone ~480,000), so paging through
  everything is not possible within the daily quota. We ask per 시도 for program names that contain
  this year or next year ("2026", "2027", "26년") and keep only rows whose application is still
  open and that are not finished or cancelled. Programs without a year in their name are missed.
- numOfRows=1000 works when a name filter is used (the unfiltered deep pages time out).

Links: prgrmNo looks like "PPG020011260820-9986258"; the number after the last '-' is the site's
kProgrmSn, so DETAIL.format(sn) is the program's own DOVOL page (plain GET, checked 2026-09-27:
title and dates on the page match the API row). Falls back to the list page if the id looks different.

Provider: the API's organisation fields (grpNm, grpTypeNm) are always empty, and actvPlcCn is the
activity *place* ("집결 장소 : ...", "미정", street addresses). The place goes to extra.place unchanged
(the site keys board entries on it); provider is the institution name found in the place
("...청소년문화의집", "...수련관", "...센터", "...도서관") or "<시군구> 자원봉사" when there is none.
"""
import re

from .. import http
from ..model import Item
from ..util import region_code, region_from_text, today, ymd

NAME = "volunteer"
LABEL = "청소년 자원봉사 (두볼)"
NEEDS_KEY = True
URL = "https://apis.data.go.kr/B552713/svc003/getYthVlntrActvtyPrgmInfo"
DETAIL = "https://www.youth.go.kr/youth/dvl/ey/vlntwkAct/vlntwkActRcritDtl.yt?kProgrmSn={}"
# DOVOL's public "봉사활동 찾기" list, used only when the program id has an unexpected shape.
PAGE = "https://www.youth.go.kr/youth/dvl/ey/vlntwkAct/vlntwkActRcritLstForm.yt?curMenuSn=434"
ROWS = 1000
# Partial-match 시도 names. Old and new official names both appear (전라북도 / 전북특별자치도).
SIDO = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원",
        "충청북", "충북", "충청남", "충남", "전라북", "전북", "전라남", "전남",
        "경상북", "경북", "경상남", "경남", "제주"]
CLOSED = {"활동완료", "활동취소"}

# A word that names an institution running youth programs. The last one in the place text wins:
# "울산광역시가족문화센터 A동 3층 울산광역시청소년활동진흥센터 교육장" -> the 진흥센터.
ORG_SUFFIX = ("문화의집", "수련관", "수련원", "센터", "도서관", "자유공간", "복지관", "혈액원", "헌혈의집",
              "학교", "재단", "협회", "진흥원", "교육청", "구청", "시청", "군청")
METRO = {"seoul": "서울", "busan": "부산", "daegu": "대구", "incheon": "인천", "gwangju": "광주",
         "daejeon": "대전", "ulsan": "울산", "sejong": "세종"}


def _rows(sido: str, name: str) -> list[dict]:
    rows: list[dict] = []
    for page in range(1, 50):
        body = http.get(URL, {"pageNo": page, "numOfRows": ROWS, "returnType": "json",
                              "actvCtpvNm": sido, "prgrmNm": name}, api_key=True, timeout=60).json()
        head = body.get("header") or {}
        if head.get("resultCode") not in ("A01001", "00"):
            raise RuntimeError(f"volunteer error {head}")
        b = body.get("body") or {}
        got = (b.get("items") or {}).get("item") or []
        if isinstance(got, dict):
            got = [got]
        rows += got
        if not got or len(rows) >= int(b.get("totalCount") or 0):
            break
    return rows


def _clean(s) -> str:
    return " ".join(str(s or "").split())


def _url(prgrm_no: str) -> str:
    sn = prgrm_no.rsplit("-", 1)[-1]
    return DETAIL.format(sn) if "-" in prgrm_no and sn.isdigit() else PAGE


def _org(place: str) -> str:
    """Institution name inside the place text, or ''."""
    text = re.sub(r"https?://\S+", " ", place)
    text = re.sub(r"^\s*집결\s*장소\s*[:：]\s*", "", text)
    text = re.split(r"활동\s*장소", text)[0]          # "집결장소: A활동장소: B" -> A
    words = [w.strip(":：.") for w in re.split(r"[\s,()\[\]/·]+", text)]
    words = [w for w in words if w]
    found = ""
    for i, w in enumerate(words):
        if len(w) >= 4 and w.endswith(ORG_SUFFIX):
            prev = words[i - 1] if i else ""
            # "광주시 청소년수련관": keep the city in front of a bare "청소년..." name
            found = f"{prev} {w}" if w.startswith("청소년") and re.fullmatch(r"\S+[시군구]", prev) else w
    return found


def _region(sido: str, sgg: str) -> str | None:
    """"전남광주통합특별시 목포시" -> jeonnam, "... 동구" -> gwangju; a plain 시도 name as before."""
    return region_from_text(f"{sido} {sgg}") or (None if "광주" in sido and "전남" in sido else region_code(sido))


def _provider(place: str, sido: str, sgg: str) -> str:
    org = _org(place)
    if org:
        return org[:60]
    metro = METRO.get(_region(sido, sgg) or "", "")
    # 남구·동구·중구 exist in many cities, so say which one
    area = f"{metro} {sgg}" if metro and sgg.endswith("구") and len(sgg) <= 3 else (sgg or sido)
    return f"{area} 자원봉사" if area else "청소년자원봉사 두볼"


def _title(name: str, years: list[str]) -> str:
    """Drop a leading "2026년 " / "2026 " / "2026. " / "2026년도 " if what is left still says something."""
    for y in years:
        m = re.match(rf"^{y}(?:년도|년|\.)?\s+(.+)$", name)
        if m:
            rest = m.group(1).strip()
            letters = len(re.sub(r"\W", "", rest))
            if letters >= 8 or (letters >= 5 and " " in rest):
                return rest
    return name


def fetch() -> list[Item]:
    now = today()
    cutoff = now.isoformat()
    names = [str(now.year), str(now.year + 1), f"{now.year % 100}년"]
    seen: dict[str, dict] = {}
    for sido in SIDO:
        for name in names:
            for row in _rows(sido, name):
                if row.get("prgrmNo"):
                    seen.setdefault(row["prgrmNo"], row)

    items: list[Item] = []
    for no, row in seen.items():
        status = _clean(row.get("vlntwkSttsSeNm"))
        apply_end = ymd(row.get("aplyPsbltyEndYmd"))
        if status in CLOSED or not apply_end or apply_end < cutoff:
            continue
        full_title = _clean(row.get("prgrmNm"))
        title = _title(full_title, names[:2])[:80]
        place = _clean(row.get("actvPlcCn"))
        sido, sgg = _clean(row.get("actvCtpvNm")), _clean(row.get("actvSggNm"))
        provider = _provider(place, sido, sgg)
        region = _region(sido, sgg)
        kind = _clean(row.get("vlntwkDtlCnNm"))
        hours = row.get("certHr")
        cost = row.get("prtcpCst") or 0
        where = _org(place) or sgg or sido
        summary = f"{where}에서 하는 {kind or '자원봉사'}예요.".strip()
        if hours:
            summary += f" 봉사시간 {hours}시간이 인정돼요."
        url = _url(no)
        extra = {k: row.get(k) for k in ("prgrmNo", "vlntwkSttsSeNm", "actvSggNm", "vlntwkDtlTypeNm",
                                         "vlntwkDtlCnNm", "certHr", "rcrtNope", "mainCn", "actcn")
                 if row.get(k) not in (None, "")}
        if place:
            extra["place"] = place[:60]
        if title != full_title:
            extra["full_title"] = full_title
        guide = _clean(row.get("actvGdDataCn"))
        if guide.startswith(("http://", "https://")):
            extra["guide_url"] = guide
        extra["how_to_apply"] = "e청소년(두볼) 봉사활동 페이지에서 로그인한 뒤 신청해요."
        items.append(Item(
            source=NAME,
            source_id=no,
            type="experience",
            title=title,
            provider=provider,
            url=url,
            summary=summary,
            apply_start=ymd(row.get("aplyPsbltyBgngYmd")),
            apply_end=apply_end,
            event_start=ymd(row.get("actvBgngYmd")),
            event_end=ymd(row.get("actvEndYmd")),
            regions=[region] if region else [],
            # DOVOL is the national youth volunteer system; the API has no separate target field.
            target_text=_clean(f"청소년 자원봉사. {_clean(row.get('refMttr'))}").rstrip(". ")[:300],
            cost_text="무료" if not cost else f"참가비 {cost}원",
            tags=["volunteer"] + ([f"volunteer:{kind}"] if kind else []),
            extra=extra,
        ))
    return items
