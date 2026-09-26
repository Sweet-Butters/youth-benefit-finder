"""큐넷 국가자격 시험일정 (한국산업인력공단, data.go.kr 15074408).

Only the qualifications our roadmap steps use are requested (config/qnet.json), one call per
qualification per year. Each exam round becomes one item: the application window is the apply date.
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
        for row in _rows(year, q):
            seq = row.get("implSeq")
            written = (ymd(row.get("docRegStartDt")), ymd(row.get("docRegEndDt")))
            practical = (ymd(row.get("pracRegStartDt")), ymd(row.get("pracRegEndDt")))
            for kind, (start, end), exam in (
                ("필기", written, (row.get("docExamStartDt"), row.get("docExamEndDt"))),
                ("실기", practical, (row.get("pracExamStartDt"), row.get("pracExamEndDt"))),
            ):
                if not end:
                    continue
                items.append(Item(
                    source=NAME,
                    source_id=f"{q['jmCd']}-{year}-{seq}-{kind}",
                    type="resource",
                    title=f"{q['name']} {year}년 {seq}회 {kind} 원서접수",
                    provider="한국산업인력공단 (큐넷)",
                    url=q["page"],
                    summary=f"{q['name']} {kind} 시험 원서접수 기간이에요. 시험 장소와 응시료는 큐넷에서 확인해요.",
                    apply_start=start, apply_end=end,
                    event_start=ymd(exam[0]), event_end=ymd(exam[1]),
                    regions=["all"],
                    tags=[f"qnet:{q['jmCd']}", "open_to_all"],
                    extra={"implYy": year, "implSeq": seq, "description": row.get("description", "")},
                ))
    return items
