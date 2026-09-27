"""기업마당 지원사업 공고 (중소벤처기업부, data.go.kr 1421000/bizinfo), youth founders only.

The feed holds every live notice (~1,500 on 2026-09-27: 4 calls at numOfRows=500), almost all for
companies (지원대상 trgetNm is 중소기업, 소상공인, 창업벤처, ...). We keep only notices a 청소년·학생·
청년 applies to as a person founding something: the title names youth, the title or field names
founding, and the title does not say the applicant is a company (config/startup-youth.json).
Many 청년 notices are employer subsidies (청년일자리도약장려금, 일경험 참여기업 모집); those are dropped.

target_text is the 지원대상 plus the 대상/자격 lines of the summary, and the title keeps its 청년/청소년
word, so youth.judge passes these by the youth words (청년 19-34 overlaps 20-24).
Same data.go.kr key as the other sources (checked 2026-09-27).
"""
import html
import json
import re
from pathlib import Path

from .. import http
from ..model import Item
from ..util import region_code, region_from_text, regions_from_text, today, ymd

NAME = "bizinfo"
LABEL = "기업마당 창업 지원 (청년)"
NEEDS_KEY = True
URL = "https://apis.data.go.kr/1421000/bizinfo/pblancBsnsService"
PAGE = "https://www.bizinfo.go.kr/sii/siia/selectSIIA200Detail.do?pblancId={}"
CONFIG = Path(__file__).resolve().parents[2] / "config" / "startup-youth.json"
ROWS = 500
TAGS = ["startup", "field:business-sales"]
# Central bodies whose notices cover the whole country when the title names no region.
NATIONAL = re.compile(r"(부|처|청|위원회)$|진흥원$|공단$|재단$")


def rules() -> dict[str, re.Pattern]:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    return {k: re.compile("|".join(cfg[k])) for k in ("youth", "founder", "company")}


def youth_startup(title: str, context: str, r: dict[str, re.Pattern]) -> bool:
    """A notice a young person applies to as a (future) founder, not one for companies."""
    return bool(r["youth"].search(title) and r["founder"].search(f"{title} {context}")
                and not r["company"].search(title))


def _text(s) -> str:
    s = re.sub(r"<br\s*/?>|</p>|</li>", "\n", str(s or ""), flags=re.I)
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


def _target(row: dict) -> str:
    """지원대상 plus the summary lines that say who may apply."""
    lines = [" ".join(x.split()) for x in _text(row.get("bsnsSumryCn")).splitlines()]
    who = [x.lstrip("☞-•·○ ") for x in lines if re.search(r"대상|자격|신청\s*가능|만\s*\d+\s*세", x)]
    return " ".join([row.get("trgetNm") or ""] + who).strip()[:300]


def _regions(title: str, org: str) -> list[str]:
    m = re.match(r"\s*\[([^\]]+)\]", title)
    if m:
        codes: list[str] = []
        for part in re.split(r"[ㆍ·,/]", m.group(1)):
            for c in regions_from_text(part) or ([region_code(part)] if region_code(part) else []):
                if c not in codes:
                    codes.append(c)
        if codes:
            return codes
    one = region_from_text(title) or region_from_text(org)
    if one:
        return [one]
    return ["all"] if org and NATIONAL.search(org) else []


def _rows() -> list[dict]:
    rows: list[dict] = []
    for page in range(1, 20):
        body = http.get(URL, {"numOfRows": ROWS, "pageNo": page, "dataType": "json"}, api_key=True, timeout=60).json()
        resp = body.get("response") or {}
        head = resp.get("header") or {}
        if head.get("resultCode") != "00":
            raise RuntimeError(f"bizinfo error {head}")
        b = resp.get("body") or {}
        got = (b.get("items") or {}).get("item") or []
        if isinstance(got, dict):
            got = [got]
        rows += got
        if not got or len(rows) >= int(b.get("totalCount") or 0):
            break
    return rows


def fetch() -> list[Item]:
    r = rules()
    cutoff = today().isoformat()
    items: list[Item] = []
    seen: set[str] = set()
    for row in _rows():
        pid = row.get("pblancId") or ""
        title = " ".join(str(row.get("pblancNm") or "").split())
        realm = row.get("pldirSportRealmLclasCodeNm") or ""
        if not pid or pid in seen or not youth_startup(title, f"{realm} {row.get('trgetNm') or ''}", r):
            continue
        period = row.get("reqstBeginEndDe") or ""
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", period)
        start, end = (ymd(dates[0]) if dates else None), (ymd(dates[1]) if len(dates) > 1 else None)
        if end and end < cutoff:
            continue
        seen.add(pid)
        org = " ".join(str(row.get("jrsdInsttNm") or "").split())
        provider = org or " ".join(str(row.get("excInsttNm") or "").split()) or "기업마당"
        url = row.get("pblancUrl") or ""
        if not url.startswith(("http://", "https://")):
            url = PAGE.format(pid)
        extra = {"pblancId": pid, "realm": realm, "trgetNm": row.get("trgetNm") or ""}
        if row.get("excInsttNm"):
            extra["exec_org"] = row["excInsttNm"]
        if row.get("reqstMthPapersCn"):
            extra["how_to_apply"] = " ".join(str(row["reqstMthPapersCn"]).split())[:200]
        if row.get("hashtags"):
            extra["hashtags"] = row["hashtags"][:200]
        items.append(Item(
            source=NAME,
            source_id=pid,
            type="support",
            title=title[:100],
            provider=provider[:60],
            url=url,
            summary=f"{provider}의 {realm or '창업'} 분야 청년·학생 창업 지원 공고예요. 자격과 지원 내용은 공고문에서 확인해요.",
            apply_start=start,
            apply_end=end,
            deadline_text="" if end else " ".join(period.split())[:40],
            regions=_regions(title, org),
            target_text=_target(row),
            tags=list(TAGS),
            extra=extra,
        ))
    return items
