"""Is this item for ages 14-24? Rules first (collection-strategy.md 4절)."""
import re

from .model import Item

MIN_AGE, MAX_AGE = 14, 24
YOUTH_WORDS = re.compile(r"청소년|학교\s*밖|중학생|고등학생|고교생|중고생|대학생|검정고시|청년|학생")
ADULT_ONLY = re.compile(r"(만\s*)?(25|30|35|40|50|65)\s*세\s*이상|성인만|노인|어르신|경로당|영유아|유아\s*대상")


def judge(item: Item) -> tuple[bool | None, str]:
    """True = youth, False = not, None = unsure (goes to review)."""
    if "open_to_all" in item.tags:
        return True, "open to all ages"
    if item.age_min is not None or item.age_max is not None:
        lo = item.age_min if item.age_min is not None else 0
        hi = item.age_max if item.age_max is not None else 200
        return (lo <= MAX_AGE and hi >= MIN_AGE), f"age {lo}-{hi}"
    text = f"{item.title} {item.target_text}"
    if ADULT_ONLY.search(text):
        return False, "adult-only words"
    if YOUTH_WORDS.search(text):
        return True, "youth words"
    return None, "no age or target info"
