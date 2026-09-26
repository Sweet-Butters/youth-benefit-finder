"""Daily collection run (collection-strategy.md 3절).

    python -m crawler.main            # all sources
    python -m crawler.main qnet       # only the named sources

Writes data/collected/items.json (kept items), review.json (unsure ones) and meta.json (per-source health).
Nothing here is shown on the site until the auto-publish decision; the site reads data/processed/ only.
"""
import datetime as dt
import json
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import attach, jev, youth
from .http import MissingKey
from .merge import merge
from .sources import ALL
from .util import KST, today

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "collected"
JEV_CACHE = OUT / "jev_cache.json"
JEV_RUNS = OUT / "jev_runs.jsonl"  # one line of Jev stats per run


def load(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def dump(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def run_source(src):
    t0 = time.time()
    try:
        return src, src.fetch(), None, time.time() - t0
    except MissingKey as e:
        return src, [], f"skipped: {e}", time.time() - t0
    except Exception as e:  # one broken source must not stop the others
        return src, [], f"{type(e).__name__}: {e}", time.time() - t0


def main(only: set[str] | None = None):
    run_date = today().isoformat()
    OUT.mkdir(parents=True, exist_ok=True)
    selected = [s for s in ALL if not only or s.NAME in only]
    with ThreadPoolExecutor(max_workers=max(1, len(selected))) as ex:
        results = list(ex.map(run_source, selected))

    previous = load(OUT / "items.json", {"items": []})["items"]
    ran = {src.NAME for src, _, err, _ in results if not err}
    previous = [r for r in previous if r["source"] not in ran]  # re-fetched sources replace their old items
    jev_cache, jev_stats, outcomes = load(JEV_CACHE, {}), None, Counter()
    if jev.available():
        jev_stats = jev.ask_all([it for _, raw, _, _ in results for it in raw], jev_cache, run_date)

    kept, review, meta = [], [], {}
    for src, raw, err, secs in results:
        n_keep = n_review = n_drop = 0
        for it in raw:
            ok, why = youth.judge(it)
            attached = attach.attach(it)
            if jev_stats is not None:
                ok, why, attached, outcome = jev.decide(it, ok, why, attached, jev_cache.get(jev.cache_key(it)))
                outcomes[outcome] += 1
            rec = it.to_dict()
            if extra_tags := attached.pop("tags_add", None):
                rec["tags"] = rec.get("tags", []) + extra_tags
            rec |= attached | {"youth_reason": why}
            reason = (why if ok is None
                      else "no matching step" if not ({"step_ids", "field_ids"} & rec.keys())
                      else "region unknown" if not rec.get("regions")
                      else "no dates" if "undated" in rec.get("tags", [])
                      else None)
            if ok is False:
                n_drop += 1
            elif reason:
                rec["review_reason"] = reason
                review.append(rec)
                n_review += 1
            else:
                kept.append(rec)
                n_keep += 1
        meta[src.NAME] = {"label": src.LABEL, "fetched": len(raw), "kept": n_keep, "review": n_review,
                          "dropped": n_drop, "error": err, "seconds": round(secs, 1)}
        print(f"{src.NAME:12} fetched={len(raw):5} kept={n_keep:4} review={n_review:4} dropped={n_drop:4} {err or ''}")

    items = merge(previous, kept, run_date)
    dump(OUT / "items.json", {"updatedAt": dt.datetime.now(KST).isoformat(timespec="seconds"), "items": items})
    dump(OUT / "review.json", {"runDate": run_date, "items": review})
    dump(OUT / "meta.json", {"runDate": run_date, "sources": meta, "total": len(items), "review": len(review),
                             "jev": dict(jev_stats, outcomes=dict(outcomes)) if jev_stats else None})
    if jev_stats:
        dump(JEV_CACHE, jev_cache)
        with JEV_RUNS.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"runDate": run_date, **jev_stats, "outcomes": dict(outcomes)}, ensure_ascii=False) + "\n")
        print(f"jev asked={jev_stats['asked']} failed={jev_stats['failed']} cost=${jev_stats['costUsd']} {dict(outcomes)}")
    print(f"total {len(items)} items, {len(review)} to review")


if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)
