"""큐넷 국가자격 시험일정 (한국산업인력공단, data.go.kr 15074408).

Only the entry-level qualifications in config/qnet.json are requested, one call per qualification
per year. Each exam round becomes one item per kind (필기, 실기): the application window is the apply date.
Items carry `qnet:<jmCd>` (the board groups by it), `open_to_all`, and `field:<id>` for each catalog field
the qualification is listed under.

정기 기능사 share one grade-wide schedule, and a round can come back with two written windows (same round,
same exam dates). The earliest window keeps the plain id `<jmCd>-<year>-<seq>-<kind>`; any later one adds its
start date, so ids never collide and stay stable between daily runs. Titles always name the qualification.
"""
import json
from pathlib import Path

from .. import http
from ..model import Item
from ..util import today, ymd

NAME = "qnet"
LABEL = "큐넷 시험일정"
NEEDS_KEY = True
URL = "https://apis.data.go.kr/B490007/qualExamSchd/getQualExamSchdList"
CONFIG = Path(__file__).resolve().parents[2] / "config" / "qnet.json"


def _rows(year: str, q: dict) -> list[dict]:
    """All rounds for one qualification; the API caps a page at 50 rows."""
    rows: list[dict] = []
    for page in range(1, 20):
        body = http.get(URL, {"numOfRows": 50, "pageNo": page, "dataFormat": "json", "implYy": year,
                              "qualgbCd": q["qualgbCd"], "jmCd": q["jmCd"]}, api_key=True).json()
        if body.get("header", {}).get("resultCode") != "00":
            raise RuntimeError(f"qnet error {body.get('header')}")
        b = body.get("body") or {}
        rows += b.get("items") or []
        if len(rows) >= int(b.get("totalCount") or 0) or not b.get("items"):
            return rows
    return rows


def fetch() -> list[Item]:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    year = str(today().year)
    items: list[Item] = []
    for q in cfg["qualifications"]:
        tags = [f"qnet:{q['jmCd']}", "open_to_all"] + [f"field:{f}" for f in q.get("fields", [])]
        rows = _rows(year, q)
        # Distinct windows per (round, kind), earliest first: that one gets the plain source id.
        windows: dict[tuple, list[tuple]] = {}
        for row in rows:
            seq = row.get("implSeq")
            for kind, pre in (("필기", "doc"), ("실기", "prac")):
                w = (ymd(row.get(f"{pre}RegStartDt")), ymd(row.get(f"{pre}RegEndDt")))
                if w[1] and w not in windows.setdefault((seq, kind), []):
                    windows[(seq, kind)].append(w)
        first = {k: min(v, key=lambda w: (w[0] or w[1], w[1])) for k, v in windows.items()}
        seen: set[str] = set()
        for row in rows:
            seq = row.get("implSeq")
            written = (ymd(row.get("docRegStartDt")), ymd(row.get("docRegEndDt")))
            practical = (ymd(row.get("pracRegStartDt")), ymd(row.get("pracRegEndDt")))
            for kind, (start, end), exam in (
                ("필기", written, (row.get("docExamStartDt"), row.get("docExamEndDt"))),
                ("실기", practical, (row.get("pracExamStartDt"), row.get("pracExamEndDt"))),
            ):
                if not end:
                    continue
                source_id = f"{q['jmCd']}-{year}-{seq}-{kind}"
                if (start, end) != first[(seq, kind)]:
                    source_id += f"-{(start or end).replace('-', '')}"
                if source_id in seen:  # the same window repeated on another row
                    continue
                seen.add(source_id)
                items.append(Item(
                    source=NAME,
                    source_id=source_id,
                    type="resource",
                    title=f"{q['name']} {year}년 {seq}회 {kind} 원서접수",
                    provider="한국산업인력공단 (큐넷)",
                    url=q["page"],
                    summary=f"{q['name']} {kind} 시험 원서접수 기간이에요. 시험 장소와 응시료는 큐넷에서 확인해요.",
                    apply_start=start, apply_end=end,
                    event_start=ymd(exam[0]), event_end=ymd(exam[1]),
                    regions=["all"],
                    tags=list(tags),
                    extra={"implYy": year, "implSeq": seq, "description": row.get("description", "")},
                ))
    return items
