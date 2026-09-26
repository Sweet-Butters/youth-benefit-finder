"""Merge items across sources and runs, compute status from dates."""
import datetime as dt
import re

from .util import today

NOISE = re.compile(r"\(.*?\)|\[.*?\]|20\d\d\s*년?|제?\s*\d+\s*(회|기|차)|모집|안내|공고|신청")


def norm(s: str) -> str:
    return re.sub(r"[^0-9a-zA-Z가-힣]", "", NOISE.sub(" ", s or "")).lower()


def key(rec: dict) -> str:
    return f"{rec['source']}:{rec['source_id']}"


def status(rec: dict) -> str:
    t = today().isoformat()
    start, end = rec.get("apply_start"), rec.get("apply_end")
    if end and end < t:
        return "closed"
    if start and start > t:
        return "upcoming"
    if end or start:
        return "open"
    return "check_deadline"  # no date: shown as "마감 확인 필요"


def merge(previous: list[dict], fresh: list[dict], run_date: str) -> list[dict]:
    by_key = {key(r): r for r in previous}
    for rec in fresh:
        old = by_key.get(key(rec))
        rec["first_seen"] = old.get("first_seen", run_date) if old else run_date
        rec["last_seen"] = run_date
        by_key[key(rec)] = rec
    # The same programme listed by two sources: keep one, remember the other.
    seen: dict[str, dict] = {}
    out = []
    for rec in sorted(by_key.values(), key=lambda r: (r["source"], r["source_id"])):
        rec["status"] = status(rec)
        dup = f"{norm(rec['title'])}|{norm(rec.get('provider', ''))}|{rec.get('apply_end') or ''}"
        if dup in seen and seen[dup]["source"] != rec["source"]:
            seen[dup].setdefault("also_in", []).append(key(rec))
            continue
        seen[dup] = rec
        out.append(rec)
    # Drop items closed for more than 60 days so the file does not grow forever.
    cutoff = (today() - dt.timedelta(days=60)).isoformat()
    return [r for r in out if not (r["status"] == "closed" and (r.get("apply_end") or "9999") < cutoff)]
