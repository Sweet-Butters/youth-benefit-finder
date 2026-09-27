"""After each daily collect: keep a short per-source history and say whether a person needs to look.

    python scripts/collect_health.py            # writes data/collected/health.json, prints problems
    python scripts/collect_health.py --weekly   # also prints the weekly summary

Problems (printed as a Markdown issue body to .health-alert.md, exit code 0 either way):
- a source failed on this run and the run before (it has worked at least once, so "key not approved yet"
  for a new source does not alert every day);
- a source fetched less than half of its median over the last 7 runs.
The collect workflow opens (or comments on) a GitHub issue when .health-alert.md is not empty.
"""
import datetime as dt
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "collected"
HISTORY = OUT / "health.json"
KEEP_RUNS = 14


def load(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def main(weekly: bool) -> None:
    meta = load(OUT / "meta.json", {})
    hist = load(HISTORY, {"runs": []})
    run = {"date": meta.get("runDate", ""), "sources": {
        name: {"fetched": s.get("fetched", 0), "kept": s.get("kept", 0), "error": s.get("error")}
        for name, s in meta.get("sources", {}).items()}}
    if not hist["runs"] or hist["runs"][-1]["date"] != run["date"]:
        hist["runs"].append(run)
    else:
        hist["runs"][-1] = run  # a second run on the same day replaces the first
    hist["runs"] = hist["runs"][-KEEP_RUNS:]
    HISTORY.write_text(json.dumps(hist, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    problems = []
    runs = hist["runs"]
    for name, now in run["sources"].items():
        past = [r["sources"].get(name) for r in runs[:-1] if r["sources"].get(name)]
        ever_ok = any(p and not p.get("error") and p.get("fetched") for p in past)
        if now.get("error") and past and past[-1].get("error") and ever_ok:
            problems.append(f"- **{name}**: 이틀 연속 실패 — `{str(now['error'])[:200]}`")
        counts = [p["fetched"] for p in past[-7:] if p and not p.get("error")]
        if not now.get("error") and len(counts) >= 3 and now["fetched"] < statistics.median(counts) / 2:
            problems.append(f"- **{name}**: 가져온 수가 평소의 절반 아래 ({now['fetched']}개, 최근 중앙값 {statistics.median(counts):.0f}개)")

    body = ""
    if problems:
        body = "## 수집 경고 (" + run["date"] + ")\n\n" + "\n".join(problems) + \
               "\n\n`data/collected/meta.json`과 Actions 로그를 보고, 출처 사이트나 API가 바뀌었는지 확인해요.\n"
    if weekly:
        body += weekly_summary(meta)
    (ROOT / ".health-alert.md").write_text(body, encoding="utf-8")
    print(body or "ok")


def weekly_summary(meta: dict) -> str:
    items = load(OUT / "items.json", {"items": []})["items"]
    week_ago = (dt.date.fromisoformat(meta["runDate"]) - dt.timedelta(days=7)).isoformat() if meta.get("runDate") else ""
    new = [i for i in items if i.get("first_seen", "") > week_ago]
    sch = [i for i in items if i.get("type") == "scholarship"]
    live = lambda xs: [i for i in xs if i.get("status") in ("open", "upcoming")]
    lines = [
        f"\n## 주간 요약 ({meta.get('runDate', '')})\n",
        f"- 전체 {len(items):,}개, 지금 신청 가능 {len(live(items)):,}개",
        f"- 장학금 {len(sch):,}개 (지금 신청 가능 {len(live(sch)):,}개)",
        f"- 이번 주 새로 들어온 것 {len(new):,}개 (장학금 {sum(1 for i in new if i.get('type') == 'scholarship'):,}개)",
        f"- 사람이 볼 검토 목록 {meta.get('review', 0):,}개 (Actions 산출물 review.json)",
        "- 출처별: " + ", ".join(f"{n} {s.get('kept', 0):,}" + (" ⚠" if s.get("error") else "")
                               for n, s in meta.get("sources", {}).items()),
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main("--weekly" in sys.argv)
