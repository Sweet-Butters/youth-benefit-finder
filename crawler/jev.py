"""Second opinion on the rules from TypeSafe's Jev model, borrowed from korea-ai-contest-tracker.

Rules decide first (youth.py, attach.py). Jev answers three typed questions with probabilities:
can a 14-24 year old apply, can an out-of-school teenager apply, and which roadmap step is it closest to.
Jev only overrides the youth verdict when it is sure (see decide()); its step answer is kept as a hint. Each distinct text is asked once and cached
in data/collected/jev_cache.json, so a daily run only sends new items. Without TYPESAFE_API_KEY, or when a
request fails, the rules decide alone.
"""
import hashlib
import json
import os
import statistics
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from .model import Item

URL = "https://api.typesafe.ai/v1/systemone"
MODEL = os.environ.get("JEV_MODEL", "jev-latest")
MAX_PER_RUN = int(os.environ.get("JEV_MAX_ITEMS", "3000"))
WORKERS = 4
DESC_CHARS = 1500
PRICE_PER_MTOK = 0.042  # USD, input tokens only

# Thresholds. Jev reads Korean less well than English, so it only overrides when sure.
YOUTH_RESCUE_ABOVE = 0.85  # an item the rules were unsure about is kept above this
YOUTH_DROP_BELOW = 0.15    # an item kept only by loose words ("학생") is dropped below this
OUT_OF_SCHOOL_ABOVE = 0.85  # tag "out_of_school_ok"
# Jev's step is only a hint for the review list: in the first full run (2026-09-27, 591 scholarships) it
# put ordinary university scholarships under "요리 대학 학과" with confidence up to 0.8. Rules attach.

# Bump when the questions change, so cached answers are asked again.
QUESTION_VERSION = 1
STEPS_DIR = Path(__file__).resolve().parent.parent / "data" / "processed" / "steps"


def _key() -> str | None:
    return os.environ.get("TYPESAFE_API_KEY", "").strip() or None


def available() -> bool:
    return bool(_key())


def _text(item: Item) -> tuple[str, str]:
    desc = " / ".join(x for x in (item.summary, item.target_text, item.cost_text, item.deadline_text) if x)
    return item.title, desc[:DESC_CHARS]


def cache_key(item: Item) -> str:
    title, desc = _text(item)
    return hashlib.sha1(f"v{QUESTION_VERSION}\n{title}\n{desc}".encode()).hexdigest()[:16]


def _steps() -> dict[str, str]:
    out = {}
    for f in sorted(STEPS_DIR.glob("*.json")):
        s = json.loads(f.read_text(encoding="utf-8"))
        out[s["id"]] = f"{s['title']}: {s.get('summary', '')[:120]}"
    out["none"] = "None of these steps"
    return out


def _questions() -> dict:
    return {
        "youth": {
            "type": "noul",
            "instructions": "Can a Korean person aged 14 to 24 (middle school, high school, out-of-school "
                            "teenager or early university student) apply to or take part in this Korean listing?",
            "criteria": {
                "true": "People aged 14-24 are eligible, or there is no age limit",
                "false": "Only adults over 24, children under 14, workers of a company, or other groups excluding 14-24",
            },
        },
        "out_of_school": {
            "type": "noul",
            "instructions": "Can a teenager who has left school (학교 밖 청소년, not enrolled in any school) apply?",
            "criteria": {
                "true": "Out-of-school teenagers are eligible, named explicitly, or eligibility does not need school enrolment",
                "false": "Applicants must be enrolled at a school or university, or teenagers are not eligible",
            },
        },
        "step": {
            "type": "choice",
            "instructions": "Which step of a young person's path toward becoming a cook is this listing most useful for?",
            "criteria": _steps(),
        },
    }


def _ask(session: requests.Session, state: dict, questions: dict, calls: list) -> dict | None:
    for attempt in range(4):
        t0 = time.perf_counter()
        try:
            r = session.post(URL, json={"state": state, "model": MODEL, "questions": questions}, timeout=30)
        except requests.RequestException:
            r = None
        row = {"ms": round((time.perf_counter() - t0) * 1000), "status": r.status_code if r is not None else 0,
               "attempt": attempt}
        calls.append(row)
        if r is not None and r.ok:
            body = r.json()
            row.update(model=body.get("model"), tokens=body.get("usage", {}).get("input_tokens", 0))
            a = body["answers"]
            return {"youth": a["youth"]["noul"], "out_of_school": a["out_of_school"]["noul"],
                    "step": a["step"]["choice"], "stepConf": a["step"]["confidence"]}
        if r is not None and r.status_code not in (429, 529) and r.status_code < 500:
            print(f"  jev {r.status_code}: {r.text[:200]}")
            return None
        retry = r.headers.get("retry-after") if r is not None else None
        time.sleep(float(retry) if retry else 2 ** attempt)
    return None


def summarize(calls: list) -> dict:
    ok = [c for c in calls if 200 <= c["status"] < 300]
    ms = sorted(c["ms"] for c in ok)
    tokens = sum(c.get("tokens", 0) for c in ok)
    pct = lambda q: ms[min(len(ms) - 1, int(q * len(ms)))] if ms else None
    return {
        "requests": len(calls), "ok": len(ok),
        "retries": sum(1 for c in calls if c["attempt"] > 0),
        "errors": dict(Counter(str(c["status"]) for c in calls if not 200 <= c["status"] < 300)),
        "latencyMs": {"p50": pct(0.5), "p95": pct(0.95), "mean": round(statistics.fmean(ms)) if ms else None},
        "inputTokens": tokens, "costUsd": round(tokens / 1e6 * PRICE_PER_MTOK, 6),
        "models": dict(Counter(c["model"] for c in ok if c.get("model"))),
    }


def ask_all(items: list[Item], cache: dict, run_date: str) -> dict:
    """Fill cache with answers for every item not asked before; return run stats."""
    todo, seen = [], set()
    for it in items:
        k = cache_key(it)
        if k in cache:
            cache[k]["seen"] = run_date
        elif k not in seen:
            seen.add(k)
            todo.append((k, it))
    todo = todo[:MAX_PER_RUN]
    calls: list = []
    if not todo:
        return dict(summarize(calls), asked=0, failed=0, cached=len(items))
    print(f"  jev: {len(todo)} new items")
    questions = _questions()
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {_key()}"

    def one(pair):
        k, it = pair
        title, desc = _text(it)
        return k, _ask(session, {"title": title, "description": desc, "provider": it.provider}, questions, calls)

    failed = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for k, ans in ex.map(one, todo):
            if ans:
                cache[k] = dict(ans, seen=run_date)
            else:
                failed += 1  # retried next run
    return dict(summarize(calls), asked=len(todo), failed=failed, cached=len(items) - len(todo))


def decide(item: Item, ok: bool | None, why: str, attached: dict, ans: dict | None) -> tuple[bool | None, str, dict, str]:
    """Combine the rule verdicts with Jev's answers. Returns (ok, why, attached, outcome)."""
    if not ans:
        return ok, why, attached, "no_answer"
    outcome = "agreed"
    firm = why in ("open to all ages",) or why.startswith("age ")  # stated facts, never overridden
    if ok is None and ans["youth"] >= YOUTH_RESCUE_ABOVE:
        ok, why, outcome = True, f"jev youth {ans['youth']:.2f}", "rescued"
    elif ok is True and not firm and ans["youth"] < YOUTH_DROP_BELOW:
        ok, why, outcome = False, f"jev not youth {ans['youth']:.2f}", "dropped"
    attached = dict(attached)
    if ans["out_of_school"] >= OUT_OF_SCHOOL_ABOVE:
        attached["tags_add"] = ["out_of_school_ok"]
    attached["jev"] = {"youth": round(ans["youth"], 2), "out_of_school": round(ans["out_of_school"], 2),
                       "step": ans["step"], "stepConf": round(ans["stepConf"], 2)}
    return ok, why, attached, outcome
