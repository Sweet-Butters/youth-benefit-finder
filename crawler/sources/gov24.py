"""보조금24 = 대한민국 공공서비스(혜택) 정보 (행정안전부, data.go.kr 15113968, api.odcloud.kr gov24/v3).

Two bulk listings per run, both paged at 1000 rows (~10,000 services -> about 11 + 11 calls, well
under the 10,000/day development quota):
- serviceList: title, provider, target text, 신청기한 ...
- supportConditions without a 서비스ID filter: age range (JA0110/JA0111) and target flags per 서비스ID.
serviceDetail is not used (one call per service would eat the quota and the list already has enough).

Only youth-relevant services are returned (is_youth), because the dataset is mostly adults, businesses
and facilities; youth.judge still runs afterwards on what is kept. Field names follow the official
swagger, copied into config/gov24.json. parse() is pure so it can be tested without a key.
"""
import json
import re
from pathlib import Path

from .. import http
from ..model import Item
from ..util import region_code, ymd

NAME = "gov24"
LABEL = "보조금24 공공서비스"
NEEDS_KEY = True
CONFIG = Path(__file__).resolve().parents[2] / "config" / "gov24.json"
PAGE_URL = "https://www.gov.kr/portal/rcvfvrSvc/dtlEx/{}"

ADULT_ONLY = re.compile(r"노인|어르신|경로당|노령|영유아|유아\s*대상|임산부|난임|출산|(만\s*)?(40|50|60|65)\s*세\s*이상")
YOUTH_WORDS = re.compile(r"청소년|학교\s*밖|중학생|고등학생|고교생|중고생|대학생|대학원생|재학생|검정고시|청년|학생|아동|장학|학자금")
OUT_OF_SCHOOL = re.compile(r"학교\s*밖")
SCHOLARSHIP = re.compile(r"장학|학자금")
DATE = re.compile(r"20\d\d\s*[./년-]\s*\d{1,2}\s*[./월-]\s*\d{1,2}")


def _cfg() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _clip(text, n: int) -> str:
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def _flag(v) -> bool:
    return v is True or str(v or "").strip().upper() in {"Y", "1", "TRUE"}


def _int(v) -> int | None:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def ages(cond: dict) -> tuple[int | None, int | None]:
    """JA0110/JA0111 -> (min, max). 0/0 or missing means the service did not say."""
    lo, hi = _int(cond.get("JA0110")), _int(cond.get("JA0111"))
    if not lo and not hi:
        return None, None
    return lo, (hi or None)


def is_youth(row: dict, cond: dict, cfg: dict) -> tuple[bool, str]:
    """Keep a service if a 14-24-year-old could plausibly use it. Order matters."""
    y = cfg["youth"]
    users = str(row.get("사용자구분") or "")
    if users and not any(u in users for u in y["person_user_types"]):
        return False, f"not for individuals ({users})"
    lo, hi = ages(cond)
    if lo is not None or hi is not None:
        a, b = lo if lo is not None else 0, hi if hi is not None else 200
        if a > y["age_max"] or b < y["age_min"]:
            return False, f"age {a}-{b} outside {y['age_min']}-{y['age_max']}"
    students = [c for c in y["student_codes"] if _flag(cond.get(c))]
    if students:
        return True, "student flag " + ",".join(students)
    text = f"{row.get('서비스명', '')} {row.get('지원대상', '')}"
    if ADULT_ONLY.search(text) and not re.search(r"청소년|학생|청년", text):
        return False, "adult-only words"
    if lo is not None or hi is not None:
        wide = y["wide_range"]
        if not ((lo or 0) <= wide["lo_at_most"] and (hi or 200) >= wide["hi_at_least"]):
            return True, f"age {lo}-{hi} overlaps"
    if YOUTH_WORDS.search(text):
        return True, "youth words"
    return False, "no youth signal"


def _dates(text: str) -> tuple[str | None, str | None]:
    found = [d for d in (ymd(re.sub(r"[년월\s]", ".", m)) for m in DATE.findall(text or "")) if d]
    if not found:
        return None, None
    return (found[0], found[-1]) if len(found) > 1 else (None, found[0])


def _regions(row: dict) -> list[str]:
    kind = str(row.get("소관기관유형") or "")
    name = str(row.get("소관기관명") or "")
    code = region_code(name)
    if code:
        return [code]
    if "중앙" in kind or "공공기관" in kind or not kind:
        return ["all"]
    return []


def to_item(row: dict, cond: dict) -> Item:
    sid = str(row.get("서비스ID") or "").strip()
    title = _clip(row.get("서비스명"), 120)
    deadline = _clip(row.get("신청기한"), 120)
    start, end = _dates(deadline)
    body = f"{title} {row.get('지원대상', '')} {row.get('지원내용', '')}"
    field_tags = [t.strip() for t in re.split(r"[,/]", str(row.get("서비스분야") or "")) if t.strip()]
    target = _clip(" / ".join(x for x in (_clip(row.get("지원대상"), 400), _clip(row.get("선정기준"), 300)) if x), 700)
    flags = [k for k, v in cond.items() if k.startswith("JA") and k not in ("JA0110", "JA0111") and _flag(v)]
    lo, hi = ages(cond)
    tags = ["gov24", *field_tags]
    if OUT_OF_SCHOOL.search(f"{title} {row.get('지원대상', '')}"):
        tags.append("out_of_school_ok")
    return Item(
        source=NAME,
        source_id=sid,
        type="scholarship" if SCHOLARSHIP.search(body) else "support",
        title=title,
        provider=_clip(row.get("소관기관명"), 80),
        url=str(row.get("상세조회URL") or "").strip() or PAGE_URL.format(sid),
        summary=_clip(row.get("서비스목적요약"), 140),
        apply_start=start, apply_end=end,
        deadline_text="" if end else deadline,
        regions=_regions(row),
        age_min=lo, age_max=hi,
        target_text=target,
        cost_text=_clip(row.get("지원내용"), 200),
        tags=tags,
        extra={k: v for k, v in {
            "신청방법": _clip(row.get("신청방법"), 200),
            "접수기관": _clip(row.get("접수기관"), 120),
            "전화문의": _clip(row.get("전화문의"), 120),
            "수정일시": row.get("수정일시"),
            "지원유형": row.get("지원유형"),
            "사용자구분": row.get("사용자구분"),
            "conditions": flags,
        }.items() if v},
    )


def parse(list_rows: list[dict], condition_rows: list[dict], cfg: dict | None = None) -> list[Item]:
    """Pure: serviceList rows + supportConditions rows -> youth-relevant Items."""
    cfg = cfg or _cfg()
    conds = {str(c.get("서비스ID")): c for c in condition_rows if c.get("서비스ID")}
    items: list[Item] = []
    seen: set[str] = set()
    for row in list_rows:
        sid = str(row.get("서비스ID") or "").strip()
        if not sid or sid in seen or not row.get("서비스명"):
            continue
        seen.add(sid)
        cond = conds.get(sid, {})
        keep, _why = is_youth(row, cond, cfg)
        if keep:
            items.append(to_item(row, cond))
    return items


def _all(op: str, cfg: dict) -> list[dict]:
    rows: list[dict] = []
    for page in range(1, cfg["max_pages"] + 1):
        try:
            body = http.get(f"{cfg['base_url']}/{op}", {"page": page, "perPage": cfg["per_page"], "returnType": "JSON"},
                            api_key=True, retries=2).json()
        except RuntimeError as e:
            if re.search(r"\b40[13]\b", str(e)):
                raise RuntimeError(f"gov24: key not approved yet ({op}: HTTP 401/403, code -4 등록되지 않은 인증키)") from None
            raise RuntimeError(f"gov24: {op} failed: {e}") from None
        except ValueError:
            raise RuntimeError(f"gov24: {op} returned non-JSON") from None
        if not isinstance(body, dict) or "data" not in body:
            code = body.get("code") if isinstance(body, dict) else None
            if code == -4:
                raise RuntimeError("gov24: key not approved yet (code -4 등록되지 않은 인증키)")
            raise RuntimeError(f"gov24: {op} error {str(body)[:200]}")
        data = body.get("data") or []
        rows += data
        if not data or len(rows) >= int(body.get("totalCount") or 0):
            return rows
    raise RuntimeError(f"gov24: {op} has more than {cfg['max_pages']} pages; raise max_pages")


def fetch() -> list[Item]:
    cfg = _cfg()
    return parse(_all("serviceList", cfg), _all("supportConditions", cfg), cfg)
