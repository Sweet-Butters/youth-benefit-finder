"""Which roadmap step (or field) does an item belong to? Rules from config/attach-rules.json."""
import json
from pathlib import Path

from .model import Item

RULES = json.loads((Path(__file__).resolve().parent.parent / "config" / "attach-rules.json").read_text(encoding="utf-8"))["rules"]


def attach(item: Item) -> dict:
    text = f"{item.title} {item.summary} {item.target_text}"
    steps: list[str] = []
    fields: list[str] = []
    for r in RULES:
        if "tag" in r and r["tag"] not in item.tags:
            continue
        if "any" in r and not any(w in text for w in r["any"]):
            continue
        if "title_any" in r and not any(w in item.title for w in r["title_any"]):
            continue
        if "any2" in r and not any(w in text for w in r["any2"]):
            continue
        if "all_types" in r and item.type not in r["all_types"]:
            continue
        steps += [s for s in r.get("step_ids", []) if s not in steps]
        fields += [f for f in r.get("field_ids", []) if f not in fields]
    out = {}
    if steps:
        out["step_ids"] = steps
    if fields:
        out["field_ids"] = fields
    return out
