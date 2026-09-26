"""청소년활동 신고프로그램 및 수련시설 (한국청소년활동진흥원, data.go.kr 15156313).

API: https://apis.data.go.kr/B552713/svc002/getYthActvtyRprtPrgmTrFcltyInfo
Required: serviceKey, pageNo, numOfRows (1000 works), returnType=JSON (or XML). Without returnType the
API answers A01003. Optional filters: trnActvNm (수련활동명, substring), certYn (Y/N), ctpvNm, sggNm.
Success is resultCode "A01001", not "00".

The table (~158,000 rows) is a log of report filings: one program appears once per status step
(작성중, 신고접수, 보완요청, 신고수리 완료 ...) and there are NO activity dates. So we do not pull it all:
we ask only for the activity-name keywords our roadmap uses (KEYWORDS), keep rows whose report was
accepted, drop titles that name a past year, and fold duplicates into one item per facility+title.
Dates stay empty; the item says to ask the facility.
"""
import hashlib
import re

from .. import http
from ..model import Item
from ..util import region_code, today

NAME = "report"
LABEL = "청소년활동 신고프로그램"
NEEDS_KEY = True
URL = "https://apis.data.go.kr/B552713/svc002/getYthActvtyRprtPrgmTrFcltyInfo"
FALLBACK_URL = "https://www.youth.go.kr/"
PAGE_SIZE = 1000

# Words in the activity name (same field words as config/attach-rules.json cooking steps).
KEYWORDS = ["요리", "조리", "제과", "제빵", "바리스타", "쿠킹", "쉐프", "셰프", "식품"]
# "푸드" was tried and dropped: mostly 푸드뱅크·푸드플랜 activities, not cooking.
# 신고가 받아들여진 상태만 (작성중·반려·보완요청 등은 버린다)
ACCEPTED = {"신고수리 완료", "변경신고 수리완료", "검토보고 확인", "변경검토 보고확인"}
COURSE_WORDS = re.compile(r"양성|과정|아카데미|교실|자격")
LEVELS = [("schboyYn", "초등학생", 8, 13), ("msklsdYn", "중학생", 14, 16),
          ("hgschstYn", "고등학생", 17, 19), ("univstYn", "대학생", 20, 24)]
GWANGJU_GU = {"동구", "서구", "남구", "북구", "광산구"}


def _rows(keyword: str) -> list[dict]:
    rows: list[dict] = []
    for page in range(1, 10):
        body = http.get(URL, {"pageNo": page, "numOfRows": PAGE_SIZE, "returnType": "JSON",
                              "trnActvNm": keyword}, api_key=True).json()
        if body.get("header", {}).get("resultCode") != "A01001":
            raise RuntimeError(f"report error {body.get('header')}")
        b = body.get("body") or {}
        got = (b.get("items") or {}).get("item") or []
        if isinstance(got, dict):
            got = [got]
        rows += got
        if not got or len(rows) >= int(b.get("totalCount") or 0):
            break
    return rows


def _norm(title: str) -> str:
    return re.sub(r"\s+", "", title.replace("&apos;", "'")).lower()


def _regions(r: dict) -> list[str]:
    ctpv = r.get("ctpvNm") or ""
    if "전남광주" in ctpv:   # merged 시도: 광주 districts vs 전남 시·군
        return ["gwangju"] if (r.get("sggNm") or "") in GWANGJU_GU else ["jeonnam"]
    code = region_code(ctpv)
    return [code] if code else []


def _past_year(title: str, year: int) -> bool:
    years = [int(y) for y in re.findall(r"(20[0-3]\d)", title)]
    return bool(years) and max(years) < year


def fetch() -> list[Item]:
    year = today().year
    seen: dict[str, Item] = {}
    for kw in KEYWORDS:
        for r in _rows(kw):
            title = (r.get("trnActvNm") or "").replace("&apos;", "'").strip()
            if not title or r.get("prgrsSttsNm") not in ACCEPTED or _past_year(title, year):
                continue
            org = r.get("brno") or r.get("fcltNm") or ""
            key = hashlib.sha1(f"{org}|{_norm(title)}".encode()).hexdigest()[:12]
            if key in seen:
                continue
            levels = [(n, lo, hi) for f, n, lo, hi in LEVELS if r.get(f) == "Y"]
            cost = str(r.get("ppPrtcpCst") or "").replace(",", "")
            home = (r.get("hmpgAddr") or "").strip()
            seen[key] = Item(
                source=NAME,
                source_id=key,
                type="course" if COURSE_WORDS.search(title) else "experience",
                title=title,
                provider=(r.get("fcltNm") or r.get("operInstNm") or r.get("lctnAddr2") or "").strip(),
                url=home if home.startswith("http") else FALLBACK_URL,
                summary="청소년 수련시설이 신고한 활동이에요. 일정과 신청 방법은 운영 기관에 물어봐요.",
                deadline_text="일정은 운영 기관에 문의",
                regions=_regions(r),
                age_min=min(lo for _, lo, _ in levels) if levels else None,
                age_max=max(hi for _, _, hi in levels) if levels else None,
                target_text=", ".join(n for n, _, _ in levels),
                cost_text="" if not cost else "무료" if cost == "0" else f"{int(cost):,}원" if cost.isdigit() else cost,
                tags=["undated"] + (["certified"] if r.get("certYn") == "Y" else []),
                extra={"status": r.get("prgrsSttsNm"), "period": r.get("actvPrdTypeNm"),
                       "lodging": r.get("ldgYn"), "highRisk": r.get("highRiskActvYn"),
                       "facilityKind": r.get("fcltKnNm"), "tel": r.get("telno"), "keyword": kw},
            )
    return list(seen.values())
