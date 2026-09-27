"""Who can apply: audience and condition tags for the site's filters (contract with web/).

    for:middle 중학생   for:high 고등학생   for:oos 학교 밖 청소년
    for:univ 대학생     for:young 청년(19-34)   for:all 누구나/제한 없음
    cond:income 소득 기준   cond:region 지역·거주 제한   cond:grade 성적 기준
    cond:special 보훈·다문화·한부모·장애·농어촌·다자녀 같은 특정 자격

Conservative on purpose: a tag only when the text (or a structured source field) says so.
Preference wording ("우선", "가점", "우대") is not a requirement and is ignored for conditions.
"""
import re

GROUP_PREFIX = ("for:", "cond:")

# Group words in eligibility text.
MIDDLE = re.compile(r"중학생|중고생|중·고생|중[·ㆍ/]\s*고등학생|중\s*고등학생")
HIGH = re.compile(r"고등학생|고교생|중고생|중·고생|고등학교\s*재학|고\s*[1-3]\s*학년|고3")
UNIV = re.compile(r"대학생|대학교?\s*재학|대학\s*신입생")
OOS = re.compile(r"학교\s*밖|학교를\s*다니지\s*않|동\s*연령대\s*청소년")
YOUNG = re.compile(r"청년")
YOUTH = re.compile(r"청소년")  # 중·고등학생 on contest and volunteer sites
# 누구나 / 제한 없음, but not "학년: 제한 없음" and the like (kosaf's per-column wording).
NOT_OPEN = re.compile(r"(학년|학과|학교|대학|전공|성적|소득|지역|거주)\s*[:：]?\s*제한\s*없음")
OPEN = re.compile(r"누구나|제한\s*없음|전\s*국민|남녀노소")
# kosaf 고등학생 files sometimes include middle schoolers explicitly.
MIDDLE_TOO = re.compile(r"중학교\s*[1-3]\s*학년\s*(~|또는|부터|및|이상)|중학생\s*이상|중학교\s*및\s*고등학교(에)?\s*재학|중\s*고등학생")

INCOME = re.compile(
    r"기초\s*생활|기초\s*수급|생계\s*[/·]?\s*의료\s*급여|수급자|차상위|소득\s*분위|소득\s*\d|[0-9]\s*분위|중위\s*소득|기준\s*중?위소득|"
    r"저소득|소득\s*구간|지원\s*구간|학자금\s*지원|소득\s*인정액|가정\s*형편|생활\s*형편|형편이\s*(어려|곤란)|"
    r"(생활|가정)이\s*(어려|곤란)|경제적\s*(사정|이유|여건|어려움|상황|도움|지원)|경제적으로\s*어려|경제\s*(수준|여건)|"
    r"재산세|재산\s*\d|건강\s*(장기요양)?\s*보험료|의료\s*보험료|불우|가계\s*소득|월\s*평균\s*소득|연간\s*수입|근로\s*소득|"
    r"복지\s*급여|생계\s*곤란|학비\s*(조달|마련|보조)|생활\s*환경이\s*어려|어려운\s*환경|구간\s*(이하|이내)")
REGION = re.compile(
    r"주민\s*등록|주소를?\s*(두|둔|둘)|주소지가|거주\s*(하는|하고|중|자|지|한)|[가-힣]{1,6}(시|군|구|도)\s*(에\s*)?거주|"
    r"관내|출신인?\s*자|소재\s*(고등학교|학교|대학)|지역\s*(연고|출신)")
# "국적, 거주지, 경력에 관계없이": a clause that lifts a limit.
NO_LIMIT = re.compile(r"[^()/·]{0,30}(관계\s*없|무관|제한\s*없)")
GRADE = re.compile(r"성적|학점|평점|\d\s*등급|석차|내신|백분위|G\.?P\.?A|학업\s*(우수|능력|성취|향상)|학습\s*능력|수능|성취도|"
                   r"평균\s*(점수\s*)?\d|\d+\s*점\s*(이상|만점)|\d\.\d\s*(이상|\(|/)|상위\s*\d|\d+\s*%\s*이내|100분의")
GRADE_NONE = re.compile(r"무관|미적용|제한\s*없")
SPECIAL = re.compile(
    r"보훈|유공자|다문화|이주\s*배경|한\s*부모|조손|장애(?!물)|농어촌|농업인|어업인|농어업인|다자녀|[2-4３]\s*자녀|세\s*자녀|셋째|"
    r"북한\s*이탈|탈북|새터민|소년\s*[·ㆍ]?\s*소녀\s*가장|보호\s*종료|자립\s*준비|아동\s*양육\s*시설|위탁\s*가정|순직|의사상자|"
    r"이\s*[·ㆍ]?\s*반장|통\s*[·ㆍ]?\s*리\s*[·ㆍ]?\s*반장|(임|재)?직원\s*(의\s*)?자녀|재직자의\s*자녀|근로자\s*자녀|조합원")
PREFERENCE = re.compile(r"우선|가점|가산점|우대")
NATIONWIDE = re.compile(r"(대한민국|국내|전국)\s*(에\s*)?(거주|주소|어디)")
UNKNOWN = {"", "기관에확인필요", "해당없음", "제한없음", "없음", "-"}


def _requirements(text: str) -> str:
    """Text with preference-only parts removed.

    kosaf joins options with " / ": "3자녀이상/ 장애인/ 저소득층 학생 우선지원" is one preference list,
    so short items right before a preference item are dropped with it."""
    parts = [p.strip() for p in re.split(r"\s*/\s*|\n", text or "")]
    keep: list[str] = []
    for p in parts:
        if PREFERENCE.search(p):
            while keep and len(keep[-1]) <= 10:
                keep.pop()
            continue
        keep.append(p)
    return " / ".join(keep)


def _field(extra: dict, name: str) -> str:
    v = (extra.get(name) or "").strip()
    return "" if re.sub(r"\s", "", v) in UNKNOWN else v


def _age_groups(lo: int | None, hi: int | None) -> set[str]:
    """Only youth-only ranges map to school groups; 0-39 says nothing about school level."""
    if lo is None and hi is None:
        return set()
    lo = 0 if lo is None else lo
    hi = 200 if hi is None else hi
    out = set()
    if hi <= 19:
        if lo <= 15 and hi >= 13:
            out.add("for:middle")
        if lo <= 18 and hi >= 16:
            out.add("for:high")
    if lo >= 18 and 24 <= hi <= 39:
        out.add("for:young")
    return out


def _text_groups(text: str) -> set[str]:
    out = set()
    if MIDDLE.search(text):
        out.add("for:middle")
    if HIGH.search(text):
        out.add("for:high")
    if UNIV.search(text):
        out.add("for:univ")
    if OOS.search(text):
        out.add("for:oos")
    if YOUNG.search(text):
        out.add("for:young")
    # Plain "청소년" (not "학교 밖 청소년" / "동 연령대 청소년") = 중·고등학생 on these sites.
    if YOUTH.search(re.sub(r"(학교\s*밖|연령대)\s*청소년", " ", text)):
        out |= {"for:middle", "for:high"}
    if OPEN.search(NOT_OPEN.sub(" ", text)):
        out.add("for:all")
    return out


def tags_for(rec: dict) -> list[str]:
    """Audience and condition tags for one collected record (dict from Item.to_dict / items.json)."""
    source, typ = rec.get("source", ""), rec.get("type", "")
    title, target = rec.get("title", "") or "", rec.get("target_text", "") or ""
    tags = set(rec.get("tags", []))
    extra = rec.get("extra", {}) or {}
    out: set[str] = set()

    # ---- who ----
    if source == "kosaf":
        # Structured: which file (고등학생 / 대학생) the scholarship came from.
        if "kosaf:hs" in tags:
            out.add("for:high")
        if "kosaf:univ" in tags:
            out.add("for:univ")
        if MIDDLE_TOO.search(target):
            out.add("for:middle")
        if OOS.search(target) or re.search(r"학교\s*밖|학교밖|꿈드림|검정고시", title):
            out.add("for:oos")
        if YOUNG.search(title):
            out.add("for:young")
    elif source == "vms1365":
        # 1365: "청소년 가능" flag; adult_ok too means anyone; age_max 18 means youth only.
        if "open_to_all" in tags:
            out.add("for:all")
        out |= _age_groups(rec.get("age_min"), rec.get("age_max"))
    else:
        groups = _text_groups(target)
        if not groups - {"for:young"} and typ in {"scholarship", "support", "contest"}:
            groups |= _text_groups(title) - {"for:all"}
        elif typ in {"scholarship", "support", "contest"} and YOUNG.search(title):
            groups.add("for:young")
        if not groups & {"for:middle", "for:high", "for:univ"}:
            groups |= _age_groups(rec.get("age_min"), rec.get("age_max"))
        else:
            groups |= _age_groups(rec.get("age_min"), rec.get("age_max")) & {"for:young"}
        if "open_to_all" in tags and source == "qnet":
            groups.add("for:all")
        out |= groups
    if "out_of_school_ok" in tags:
        out.add("for:oos")

    # ---- conditions ----
    # Titles of volunteer/experience items describe who is served ("장애인 활동 보조"), not who applies.
    cond_text = _requirements(target)
    if typ in {"scholarship", "support"}:
        cond_text += " / " + title
    income = _requirements(_field(extra, "income")) if source == "kosaf" else ""
    grade = _field(extra, "grade") if source == "kosaf" else ""
    residence = _field(extra, "residence") if source == "kosaf" else ""
    if NATIONWIDE.match(residence):
        residence = ""
    aid = extra.get("aid_kind", "") if source == "kosaf" else ""

    if INCOME.search(cond_text) or INCOME.search(income) or aid == "소득구분":
        out.add("cond:income")
    if REGION.search(NO_LIMIT.sub(" ", cond_text)) or residence or aid == "지역연고":
        out.add("cond:region")
    if (grade and GRADE.search(grade) and not (GRADE_NONE.search(grade) and not re.search(r"\d", grade))) \
            or aid == "성적우수" or re.search(r"성적\s*(우수|기준|평균|상위)|학점\s*이상|평점|석차|내신", cond_text):
        out.add("cond:grade")
    if SPECIAL.search(cond_text) or SPECIAL.search(income) or aid == "장애인":
        out.add("cond:special")
    return sorted(out)


def apply(rec: dict) -> dict:
    """Replace a record's for:/cond: tags with freshly computed ones (idempotent)."""
    base = [t for t in rec.get("tags", []) if not t.startswith(GROUP_PREFIX)]
    rec["tags"] = list(dict.fromkeys(base + tags_for({**rec, "tags": base})))
    return rec
