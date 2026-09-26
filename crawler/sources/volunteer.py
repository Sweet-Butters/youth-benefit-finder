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
"""
from .. import http
from ..model import Item
from ..util import region_code, today, ymd

NAME = "volunteer"
LABEL = "청소년 자원봉사 (두볼)"
NEEDS_KEY = True
URL = "https://apis.data.go.kr/B552713/svc003/getYthVlntrActvtyPrgmInfo"
# The API has no per-program page we can link to; this is DOVOL's public "봉사활동 찾기" list.
PAGE = "https://www.youth.go.kr/youth/dvl/ey/vlntwkAct/vlntwkActRcritLstForm.yt?curMenuSn=434"
ROWS = 1000
# Partial-match 시도 names. Old and new official names both appear (전라북도 / 전북특별자치도).
SIDO = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원",
        "충청북", "충북", "충청남", "충남", "전라북", "전북", "전라남", "전남",
        "경상북", "경북", "경상남", "경남", "제주"]
CLOSED = {"활동완료", "활동취소"}


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
        title = _clean(row.get("prgrmNm"))[:80]
        place = _clean(row.get("actvPlcCn"))
        provider = (_clean(row.get("grpNm")) or place or "한국청소년활동진흥원 (두볼)")[:60]
        sido, sgg = _clean(row.get("actvCtpvNm")), _clean(row.get("actvSggNm"))
        region = region_code(sido)
        kind = _clean(row.get("vlntwkDtlCnNm"))
        hours = row.get("certHr")
        cost = row.get("prtcpCst") or 0
        summary = f"{sgg or sido} {place}에서 하는 {kind or '자원봉사'}예요.".replace("  ", " ")
        if hours:
            summary += f" 봉사시간 {hours}시간이 인정돼요."
        items.append(Item(
            source=NAME,
            source_id=no,
            type="experience",
            title=title,
            provider=provider,
            url=PAGE,
            summary=summary,
            apply_start=ymd(row.get("aplyPsbltyBgngYmd")),
            apply_end=apply_end,
            event_start=ymd(row.get("actvBgngYmd")),
            event_end=ymd(row.get("actvEndYmd")),
            regions=[region] if region else [],
            # DOVOL is the national youth volunteer system; the API has no separate target field.
            target_text=_clean(f"청소년 자원봉사 (두볼) {_clean(row.get('refMttr'))}")[:300],
            cost_text="무료" if not cost else f"참가비 {cost}원",
            tags=["volunteer"] + ([f"volunteer:{kind}"] if kind else []),
            extra={k: row.get(k) for k in ("prgrmNo", "vlntwkSttsSeNm", "actvSggNm", "actvPlcCn",
                                          "vlntwkDtlTypeNm", "vlntwkDtlCnNm", "certHr", "rcrtNope",
                                          "mainCn", "actcn") if row.get(k) not in (None, "")},
        ))
    return items
