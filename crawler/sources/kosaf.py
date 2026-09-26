"""한국장학재단 학자금지원정보 (고등학생 15116988, 대학생 15028252; data.go.kr 파일데이터).

No API key: each run reads the dataset page for the current CSV link (it changes with every new
edition) and falls back to the link in config/kosaf.json. Files are cp949. One row = one scholarship.
Rows that closed long ago are skipped (merge.py would drop them anyway).
"""
import csv
import datetime as dt
import hashlib
import io
import json
import re
from pathlib import Path

from .. import http
from ..model import Item
from ..util import regions_from_text, today, ymd

NAME = "kosaf"
LABEL = "한국장학재단 학자금지원정보"
NEEDS_KEY = False
CONFIG = Path(__file__).resolve().parents[2] / "config" / "kosaf.json"
CSV_LINK = re.compile(r'"contentUrl"\s*:\s*"(https://www\.data\.go\.kr/cmm/cmm/fileDownload\.do\?[^"]+)"')
NONE_WORDS = {"", "해당없음", "제한없음", "없음", "-"}


def _csv_url(ds: dict) -> str:
    try:
        m = CSV_LINK.search(http.get(ds["page"]).text)
        if m:
            return m.group(1).replace("&amp;", "&")
    except Exception:
        pass
    return ds["fallback_csv"]


def _rows(url: str) -> list[dict]:
    raw = http.get(url, timeout=90).content
    for enc in ("cp949", "utf-8-sig"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("cp949", errors="replace")
    return [{(k or "").strip(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(io.StringIO(text))]


NOTE = re.compile(r"^자세한\s*(사항|내용)은.*(참고|참조)\S*$")   # "※ 자세한 사항은 첨부파일 또는 홈페이지 참고"
ASK = re.compile(r"^(기관|대학)\s*확인\s*필요$")


def _parts(s: str) -> list[str]:
    """'○ 60만원○ 추가※ 자세한 사항은 … 참고' -> ['60만원', '추가']; boilerplate notes and 해당없음 dropped."""
    out: list[str] = []
    for p in re.split(r"[○●※ㆍ]|(?:^|\s)ㅇ", s or ""):
        p = re.sub(r"\s+", " ", p).strip(" -·")
        if not p or p in NONE_WORDS or NOTE.match(p):
            continue
        p = ASK.sub(lambda m: f"{m.group(1)}에 확인 필요", p)
        if p not in out:
            out.append(p)
    return out


def _val(s: str) -> str:
    """'○ 60만원○ 추가' -> '60만원 / 추가'; '' when it says nothing."""
    return " / ".join(_parts(s))


# The file glues every ticked option together ('1학년2학년3학년제한없음'). Known options, longest first.
OPTIONS = sorted([
    "제한없음", "해당없음", "연령제한",
    "과학고", "국제고", "마이스터고", "영재고", "예술고", "외국어고", "일반고", "자율고", "체육고", "특성화고",
    "4년제(5~6년제포함)", "전문대(2~3년제)", "기술대학", "원격대학", "일반대학원", "전문대학원", "학점은행제 대학",
    "해외대학", "특정대학",
    "1학년", "2학년", "3학년", "대학신입생", "대학8학기이상", *[f"대학{n}학기" for n in range(2, 8)],
    "박사과정", "석사2학기이상", "석사신입생(1학기)",
    "공학계열", "교육계열", "사회계열", "예체능계열", "의약계열", "인문계열", "자연계열", "특정학과",
], key=len, reverse=True)
OPTION_RE = re.compile("|".join(re.escape(o) for o in OPTIONS))
HIGH_SCHOOLS = ["과학고", "국제고", "마이스터고", "영재고", "예술고", "외국어고", "일반고", "자율고", "체육고", "특성화고"]
FIELDS = ["공학계열", "교육계열", "사회계열", "예체능계열", "의약계열", "인문계열", "자연계열"]
GRADUATE = {"석사신입생(1학기)": "석사 신입생", "석사2학기이상": "석사 2학기 이상", "박사과정": "박사과정"}
LABELS = {"4년제(5~6년제포함)": "4년제", "전문대(2~3년제)": "전문대", "학점은행제 대학": "학점은행제",
          "특정대학": "특정 대학", "특정학과": "특정 학과", "연령제한": "연령 제한 있음", **GRADUATE}


def _options(s: str) -> list[str]:
    """'1학년2학년3학년' -> ['1학년', '2학년', '3학년']; text that is not a known option stays one piece."""
    out, pos = [], 0
    for m in OPTION_RE.finditer(s or ""):
        if s[pos:m.start()].strip():
            out.append(s[pos:m.start()].strip())
        out.append(m.group(0))
        pos = m.end()
    if s and s[pos:].strip():
        out.append(s[pos:].strip())
    return out


def _span(nums: list[int]) -> str:
    """[2, 3, 4, 6, 7] -> '2~4·6·7'."""
    runs: list[list[int]] = []
    for n in sorted(set(nums)):
        if runs and n == runs[-1][-1] + 1:
            runs[-1].append(n)
        else:
            runs.append([n])
    return "·".join(f"{r[0]}~{r[-1]}" if len(r) > 2 else "·".join(map(str, r)) for r in runs)


def _choice(s: str, kind: str) -> str:
    """Readable form of one glued option column ('대학 신입생, 2~8학기 이상'); '' when it is 해당없음."""
    opts = [o for o in _options(s) if o != "해당없음"]
    if not opts:
        return ""
    if "제한없음" in opts:
        return "제한 없음"
    if kind == "school":
        hs = [o for o in HIGH_SCHOOLS if o in opts]
        if len(hs) == len(HIGH_SCHOOLS):
            hs_text = "모든 고교"
        elif len(hs) >= 7:
            hs_text = f"모든 고교({'·'.join(o for o in HIGH_SCHOOLS if o not in hs)} 제외)"
        else:
            hs_text = "·".join(hs)
        return ", ".join(x for x in [hs_text, *(LABELS.get(o, o) for o in opts if o not in HIGH_SCHOOLS)] if x)
    if kind == "grade":
        out = []
        years = sorted(int(o[0]) for o in opts if re.fullmatch(r"\d학년", o))
        if years:
            out.append(f"{'·'.join(map(str, years))}학년")
        terms = [int(re.search(r"\d", o).group()) for o in opts if re.fullmatch(r"대학\d학기(이상)?", o)]
        term_text = f"{_span(terms)}학기" + (" 이상" if "대학8학기이상" in opts else "") if terms else ""
        if "대학신입생" in opts:
            out.append("대학 신입생" + (f", {term_text}" if term_text else ""))
        elif term_text:
            out.append(f"대학 {term_text}")
        out += [LABELS[o] for o in [*GRADUATE, "연령제한"] if o in opts]
        out += [o for o in opts if o not in OPTIONS]
        return ", ".join(out)
    if kind == "field":
        fs = [o for o in FIELDS if o in opts]
        fs_text = "모든 계열" if len(fs) == len(FIELDS) else ("·".join(f[:-2] for f in fs) + "계열" if fs else "")
        return ", ".join(x for x in [fs_text, *(LABELS.get(o, o) for o in opts if o not in FIELDS)] if x)
    return ", ".join(LABELS.get(o, o) for o in opts)


def _regions(row: dict) -> list[str]:
    """Province codes; ['all'] when there is no residence rule; [] when the rule's place is unclear."""
    provider = row.get("운영기관명", "")
    if row.get("운영기관구분", "").startswith("지자체"):
        codes = regions_from_text(provider)
        if codes:
            return codes
    raw = row.get("지역거주여부 상세내용", "")
    live = _val(raw)
    codes = regions_from_text(live)
    if codes:
        return codes
    # "관내", "발전소 주변지역", "※ 자세한 사항은 … 참고": a rule exists; the place, if anywhere, is in the name.
    # A 지역연고 scholarship with no rule written ("음성군장학회") is local too when its name says where.
    has_rule = bool(live or re.sub(r"[\s○●※ㅇ-]|해당없음|제한없음|없음", "", raw))
    if has_rule or row.get("학자금유형구분") == "지역연고":
        for text in (provider, row.get("상품명", "")):
            codes = regions_from_text(text)
            if codes:
                return codes
    return [] if has_rule else ["all"]


def _josa(word: str, pair: str) -> str:
    """_josa('서류심사', '으로/로') -> '로'; '면접' -> '으로'; '을/를' likewise."""
    c = word[-1] if word else ""
    final = (ord(c) - 0xAC00) % 28 if "가" <= c <= "힣" else 0
    a, b = pair.split("/")
    if pair == "으로/로" and final == 8:   # ㄹ받침 takes 로
        return b
    return a if final else b


def _won(money: str) -> list[int]:
    """Amounts in 원: '성적 상위 30% 각 100만원 / 60만원' -> [1000000, 600000]; '50~100만원' counts both."""
    money = re.sub(r"(\d)\s*~\s*(\d[\d,.]*\s*(억|천만|백만|만|천))", r"\1\3원~\2", money)
    out = []
    for m in re.finditer(r"(\d[\d,]*(?:\.\d+)?)\s*(억|천만|백만|만|천)?\s*원", money):
        n = float(m.group(1).replace(",", ""))
        n *= {"억": 1e8, "천만": 1e7, "백만": 1e6, "만": 1e4, "천": 1e3}.get(m.group(2) or "", 1)
        if n >= 10000:
            out.append(int(n))
    return out


def _man(n: int) -> str:
    """1000000 -> '100만원', 175000 -> '17.5만원', 12790 -> '12,790원'."""
    if n % 1000:
        return f"{n:,}원"
    return f"{n / 1e4:,.1f}".removesuffix(".0") + "만원"


# Money text is free prose; say the amount only when it cannot be misread.
NOT_A_SUM = re.compile(r"전액|실비|실납|실제|소요액|시급|이자|대출|이율|상환|\+|및|추가|별도|분할|씩")
PER = [(re.compile(r"학기당|매\s*학기|한\s*학기|학기별"), "학기마다 "), (re.compile(r"(?<![가-힣])월|매월|매달"), "매달 "),
       (re.compile(r"(?<![가-힣])연(?![가-힣])|연간"), "1년에 ")]
UP_TO = re.compile(r"(최대|최고)\s*\d[\d,.]*\s*(억|천만|백만|만|천)?\s*원|원\s*(이내|한도|범위)")   # next to the amount, not "최대 4학기"


def _money_phrase(money: str) -> str:
    """'100만원' -> '100만원을 받', '학기당 200만 원 … 지원' -> '학기마다 200만원을 받', tiers -> '60만~100만원을 받'."""
    if not money:
        return ""
    if NOT_A_SUM.search(money):
        full = re.search(r"(등록금|수업료)\s*전액", money)
        simple = not _won(money) and not re.search(r"또는|\+|및|이자|대출|/", money)
        return f"{full.group(1)} 전액을 받" if full and simple else ""
    amounts = _won(money)
    if len(amounts) == 1:
        per = next((word for pat, word in PER if pat.search(money)), "")
        if UP_TO.search(money):
            return f"{per}최대 {_man(amounts[0])}까지 받"
        return f"{per}{_man(amounts[0])}을 받"
    parts = money.split(" / ")
    tiers = len(amounts) > 1 and len(parts) == len(amounts) and all(len(_won(p)) == 1 for p in parts)
    if tiers and not any(pat.search(money) for pat, _ in PER) and not UP_TO.search(money):
        lo, hi = _man(min(amounts)), _man(max(amounts))
        if lo == hi:
            return f"{hi}을 받"
        return f"{lo.removesuffix('원') if lo.endswith('만원') and hi.endswith('만원') else lo}~{hi}을 받"
    if len(amounts) == 2 and len(parts) == 1 and re.search(r"\d\s*(만\s*)?원?\s*~", money) and not UP_TO.search(money):
        lo, hi = _man(min(amounts)), _man(max(amounts))
        return f"{lo.removesuffix('원') if lo.endswith('만원') and hi.endswith('만원') else lo}~{hi}을 받"
    return ""


WHO = {"성적우수": "성적이 좋은 ", "소득구분": "형편이 어려운 ", "장애인": "장애가 있는 ", "특기자": "특기가 있는 ",
       "지역연고": "지역에 연고가 있는 "}
METHOD_END = re.compile(r"(심사|면접|추천|심의|평가|추첨|선정|시험)$")


def _summary(ds: dict, provider: str, kind: str, money: str, selection: str, recommendation: str) -> str:
    """Two short sentences: who it is for, then how much and how people are picked, when the file says."""
    first = f"{WHO.get(kind, '')}{ds['label']}을 위한 {provider}의 장학금이에요."
    money_bit = _money_phrase(money)
    bits = [money_bit] if money_bit else []
    sel = selection if len(selection) <= 30 and "/" not in selection else ""
    if sel and METHOD_END.search(sel):
        bits.append(f"{sel}{_josa(sel, '으로/로')} 뽑아요")
    elif recommendation.endswith("추천") and len(recommendation) <= 15:
        bits.append(f"{recommendation}이 필요해요")
    if not bits:
        return first + " 자격과 서류는 공고에서 확인해요."
    if bits[0].endswith("받"):
        bits[0] += "고" if len(bits) > 1 else ("아요" if not bits[0].endswith("까지 받") else "을 수 있어요")
    return f"{first} {', '.join(bits)}."


def _title(title: str, provider: str) -> str:
    """Whitespace tidied; the provider is put in front only when the title does not already carry it."""
    title = re.sub(r"\s+", " ", title).strip()
    core = lambda s: re.sub(r"\(재\)|\(사\)|\(주\)|재단법인|사단법인|주식회사|\s", "", s)
    if provider in title or (core(provider) and core(provider) in core(title)):
        return title
    return f"{provider} {title}"


def _item(ds: dict, row: dict) -> Item:
    title = row.get("상품명", "")
    provider = re.sub(r"\s+", " ", row.get("운영기관명", "")).strip()
    school = _choice(row.get("학교구분") or row.get("대학구분") or "", "school")
    grade = _choice(row.get("학년구분", ""), "grade")
    field_ = _choice(row.get("학과구분", ""), "field")
    qual = _val(row.get("특정자격 상세내용", ""))
    target = " · ".join(x for x in (
        f"{ds['label']} 대상",
        f"{'학교' if ds['key'] == 'hs' else '대학'}: {school}" if school else "",
        f"학년: {grade}" if grade else "", f"학과: {field_}" if field_ else "", qual,
    ) if x)
    money = _val(row.get("지원내역 상세내용", ""))
    kind = row.get("학자금유형구분", "")
    kind = "" if kind in NONE_WORDS else kind
    selection = _val(row.get("선발방법 상세내용", ""))
    recommendation = _val(row.get("추천필요여부 상세내용", ""))
    # Keyed on the raw names so ids stay the same as before the whitespace clean-up.
    sid = hashlib.sha1(f"{ds['key']}|{row.get('운영기관명', '')}|{title}".encode("utf-8")).hexdigest()[:12]
    home = (row.get("홈페이지주소") or row.get("홈페이지 주소") or "").strip()
    return Item(
        source=NAME,
        source_id=f"{ds['key']}-{sid}",
        type="scholarship",
        title=_title(title, provider),
        provider=provider,
        url=home if home.startswith("http") else ds["page"],
        summary=_summary(ds, provider, kind, money, selection, recommendation),
        apply_start=ymd(row.get("모집시작일")),
        apply_end=ymd(row.get("모집종료일")),
        regions=_regions(row),
        target_text=target,
        cost_text=money,
        tags=[f"kosaf:{ds['key']}"],
        extra={k: v for k, v in {
            "dataset": ds["page"],
            "provider_kind": row.get("운영기관구분", ""),
            "aid_kind": kind,
            "grade": _val(row.get("성적기준 상세내용", "")),
            "income": _val(row.get("소득기준 상세내용", "")),
            "residence": _val(row.get("지역거주여부 상세내용", "")),
            "selection": selection,
            "quota": _val(row.get("선발인원 상세내용", "")),
            "recommendation": recommendation,
            "documents": _val(row.get("제출서류 상세내용", "")),
            "restrictions": _val(row.get("자격제한 상세내용", "")),
        }.items() if v},
    )


def fetch() -> list[Item]:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    cutoff = (today() - dt.timedelta(days=int(cfg.get("keep_closed_days", 60)))).isoformat()
    items: list[Item] = []
    seen: set[str] = set()
    for ds in cfg["datasets"]:
        for row in _rows(_csv_url(ds)):
            if not row.get("상품명"):
                continue
            it = _item(ds, row)
            if (it.apply_end or "9999") < cutoff or it.source_id in seen:
                continue
            seen.add(it.source_id)
            items.append(it)
    return items
