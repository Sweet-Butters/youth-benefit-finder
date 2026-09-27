"""Is this item for ages 14-24? Rules first (collection-strategy.md 4절)."""
import re

from .model import Item

MIN_AGE, MAX_AGE = 14, 24
YOUTH_WORDS = re.compile(r"청소년|학교\s*밖|중학생|고등학생|고교생|중고생|대학생|검정고시|청년|(?<!초등)학생")
# Anyone may apply: 누구나, 제한 없음, 전 국민 (common contest wording).
OPEN_WORDS = re.compile(r"누구나|(대상\s*)?제한\s*없음|전\s*국민|남녀노소")
ADULT_ONLY = re.compile(r"(만\s*)?(25|30|35|40|50|65)\s*세\s*이상|성인만|노인|어르신|경로당|영유아|유아\s*대상")
# Only young children: 초등학생·어린이·유치원 with no older group named.
CHILD_ONLY = re.compile(r"초등학생|어린이|유치원|유아")


def judge(item: Item) -> tuple[bool | None, str]:
    """True = youth, False = not, None = unsure (goes to review)."""
    if "open_to_all" in item.tags:
        return True, "open to all ages"
    if item.age_min is not None or item.age_max is not None:
        lo = item.age_min if item.age_min is not None else 0
        hi = item.age_max if item.age_max is not None else 200
        return (lo <= MAX_AGE and hi >= MIN_AGE), f"age {lo}-{hi}"
    text = f"{item.title} {item.target_text}"
    target = item.target_text or ""
    # Explicit youth groups in the target win over words about who is served ("어르신 말벗", "주부 및 영유아").
    if YOUTH_WORDS.search(target) or OPEN_WORDS.search(target):
        return True, "youth words in target"
    if CHILD_ONLY.search(target):
        return False, "children only"
    if ADULT_ONLY.search(text):
        return False, "adult-only words"
    if YOUTH_WORDS.search(text) or OPEN_WORDS.search(text):
        return True, "youth words"
    return None, "no age or target info"
