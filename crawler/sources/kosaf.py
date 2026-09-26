"""한국장학재단 학자금지원정보 (고등학생 15116988, 대학생 15028252; data.go.kr 파일데이터).

No API key: each run reads the dataset page for the current CSV link (it changes with every new
edition) and falls back to the link in config/kosaf.json. Files are cp949. One row = one scholarship.
Rows that closed long ago are skipped (merge.py would drop them anyway).
"""
import csv
import datetime as dt
import hashlib
import io
import json
import re
from pathlib import Path

from .. import http
from ..model import Item
from ..util import region_code, today, ymd

NAME = "kosaf"
LABEL = "한국장학재단 학자금지원정보"
NEEDS_KEY = False
CONFIG = Path(__file__).resolve().parents[2] / "config" / "kosaf.json"
CSV_LINK = re.compile(r'"contentUrl"\s*:\s*"(https://www\.data\.go\.kr/cmm/cmm/fileDownload\.do\?[^"]+)"')
NONE_WORDS = {"", "해당없음", "제한없음", "없음", "-"}


def _csv_url(ds: dict) -> str:
    try:
        m = CSV_LINK.search(http.get(ds["page"]).text)
        if m:
            return m.group(1).replace("&amp;", "&")
    except Exception:
        pass
    return ds["fallback_csv"]


def _rows(url: str) -> list[dict]:
    raw = http.get(url, timeout=90).content
    for enc in ("cp949", "utf-8-sig"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("cp949", errors="replace")
    return [{(k or "").strip(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(io.StringIO(text))]


def _clean(s: str) -> str:
    """'○ 60만원○ 추가' -> '60만원 / 추가'."""
    parts = [p.strip(" ※-") for p in re.split(r"[○●]", s or "")]
    return " / ".join(p for p in parts if p)


def _val(s: str) -> str:
    s = _clean(s)
    return "" if s in NONE_WORDS else s


def _choice(s: str) -> str:
    """The file glues every ticked option together ('1학년2학년3학년제한없음'); '제한없음' wins."""
    return "제한없음" if "제한없음" in s else s


def _regions(row: dict) -> list[str]:
    if row.get("운영기관구분", "").startswith("지자체"):
        prov = row.get("운영기관명", "")
        code = region_code(prov.split()[0] if prov else "") or region_code(prov)
        if code:
            return [code]
    live = _val(row.get("지역거주여부 상세내용", ""))
    code = region_code(live.split()[0] if live else "") or region_code(live)
    if code:
        return [code]
    # A residence rule naming only a city or county (홍천군, 당진): not nationwide, region unknown.
    return [] if live else ["all"]


def _item(ds: dict, row: dict) -> Item:
    title = row.get("상품명", "")
    provider = row.get("운영기관명", "")
    school = _choice(row.get("학교구분") or row.get("대학구분") or "")
    grade = _choice(row.get("학년구분", ""))
    qual = _val(row.get("특정자격 상세내용", ""))
    target = " ".join(x for x in (
        f"{ds['label']} 대상", f"학교: {school}" if school else "", f"학년: {grade}" if grade else "",
        f"학과: {_choice(row['학과구분'])}" if row.get("학과구분") else "", qual,
    ) if x)
    money = _val(row.get("지원내역 상세내용", ""))
    kind = row.get("학자금유형구분", "")
    sid = hashlib.sha1(f"{ds['key']}|{provider}|{title}".encode("utf-8")).hexdigest()[:12]
    home = (row.get("홈페이지주소") or row.get("홈페이지 주소") or "").strip()
    return Item(
        source=NAME,
        source_id=f"{ds['key']}-{sid}",
        type="scholarship",
        title=title if provider in title else f"{provider} {title}",
        provider=provider,
        url=home if home.startswith("http") else ds["page"],
        summary=f"{ds['label']}을 위한 {provider}의 장학금이에요"
                + (f" ({kind})" if kind and kind not in NONE_WORDS else "")
                + ". 자격과 서류는 공고에서 확인해요.",
        apply_start=ymd(row.get("모집시작일")),
        apply_end=ymd(row.get("모집종료일")),
        regions=_regions(row),
        target_text=target,
        cost_text=money,
        tags=[f"kosaf:{ds['key']}"],
        extra={k: v for k, v in {
            "dataset": ds["page"],
            "provider_kind": row.get("운영기관구분", ""),
            "aid_kind": kind,
            "grade": _val(row.get("성적기준 상세내용", "")),
            "income": _val(row.get("소득기준 상세내용", "")),
            "residence": _val(row.get("지역거주여부 상세내용", "")),
            "selection": _val(row.get("선발방법 상세내용", "")),
            "quota": _val(row.get("선발인원 상세내용", "")),
            "recommendation": _val(row.get("추천필요여부 상세내용", "")),
            "documents": _val(row.get("제출서류 상세내용", "")),
            "restrictions": _val(row.get("자격제한 상세내용", "")),
        }.items() if v},
    )


def fetch() -> list[Item]:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    cutoff = (today() - dt.timedelta(days=int(cfg.get("keep_closed_days", 60)))).isoformat()
    items: list[Item] = []
    seen: set[str] = set()
    for ds in cfg["datasets"]:
        for row in _rows(_csv_url(ds)):
            if not row.get("상품명"):
                continue
            it = _item(ds, row)
            if (it.apply_end or "9999") < cutoff or it.source_id in seen:
                continue
            seen.add(it.source_id)
            items.append(it)
    return items
