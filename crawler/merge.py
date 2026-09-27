"""Merge items across sources and runs, compute status from dates."""
import datetime as dt
import re

from .util import today

KEEP_CLOSED = {"kosaf"}
NOISE = re.compile(r"\(.*?\)|\[.*?\]|20\d\d\s*년?|제?\s*\d+\s*(회|기|차)|모집|안내|공고|신청")

# Contests: the same call is listed on several contest sites with different wrapping —
# "[청주공예비엔날레] 2027 청주국제공예공모전", "제1회 [자갈치문학상] 공모", "… 영상 공모전 | 최고 상금 100만 원! (~10/17)".
MIN_CONTEST_KEY = 6  # shorter keys ("섬여행영상") are too generic to merge on title alone
_PAREN = re.compile(r"\([^()]*\)|\[[^\[\]]*\]|【[^【】]*】|〔[^〔〕]*〕")
_QUOTED = re.compile(r"「[^「」]*」|『[^『』]*』|<[^<>]*>|《[^《》]*》|〈[^〈〉]*〉|‘[^‘’]*’|“[^“”]*”|'[^']*'|\"[^\"]*\"")
_CONTEST_NOISE = re.compile(
    r"20\d\d\s*(년도|학년도|년)?\.?|제\s*\d+\s*(회|기|차)|\d+\s*(회|기|차)\b|"
    r"공모전|공모|모집|공고|안내|기간\s*연장|접수\s*연장")


def norm(s: str) -> str:
    return re.sub(r"[^0-9a-zA-Z가-힣]", "", NOISE.sub(" ", s or "")).lower()


SPELLING = (("쉐", "셰"), ("컨텐츠", "콘텐츠"), ("페스티발", "페스티벌"))


def _squash(s: str) -> str:
    s = re.sub(r"[^0-9a-zA-Z가-힣]", "", _CONTEST_NOISE.sub(" ", s)).lower()
    for a, b in SPELLING:
        s = s.replace(a, b)
    return s


def contest_norm(title: str) -> str:
    """Strong title key for contests: brackets, quotes, 회차, years and 공모전/공모/모집 removed.

    Bracketed or quoted parts are dropped when the rest still says enough (they are usually the host
    or a slogan); otherwise their text is kept ("제1회 [자갈치문학상] 공모" -> "자갈치문학상")."""
    s = (title or "").split(" | ")[0]
    for pat in (_PAREN, _QUOTED):
        dropped = pat.sub(" ", s)
        s = dropped if len(_squash(dropped)) >= MIN_CONTEST_KEY else re.sub(r"[()\[\]【】〔〕「」『』<>《》〈〉‘’“”'\"]", " ", s)
    return _squash(s)


def quoted_names(title: str) -> set[str]:
    """Names in quote marks ("'더로드셰프 한강' 청년 셰프 모집"): sites reword the rest but keep the name.
    Square brackets are left out: they usually hold the host, which runs many different contests."""
    names = {_squash(m.group(0)) for m in _QUOTED.finditer((title or "").split(" | ")[0])}
    return {n for n in names if len(n) >= MIN_CONTEST_KEY}


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


def _richness(rec: dict) -> tuple:
    """Which listing of a merged contest to show: the most specific target, a real host, dates, categories."""
    target = rec.get("target_text", "")
    tokens = [t for t in re.split(r"[,·/]", target) if t.strip()]
    generic_target = bool(re.fullmatch(r"\s*(대상\s*)?제한\s*없음\s*|\s*", target))
    hosts = (rec.get("extra") or {}).get("hosts") or []
    site = (rec.get("extra") or {}).get("site", "")
    real_host = bool(rec.get("provider")) and rec.get("provider") not in {site, "링커리어", "씽굿", "위비티", "올콘", "콘테스트코리아"}
    return (not generic_target, len(tokens), real_host, len(hosts), bool(rec.get("apply_start")),
            bool((rec.get("extra") or {}).get("category")))


class _Groups:
    def __init__(self):
        self.parent: dict[str, str] = {}

    def find(self, k: str) -> str:
        self.parent.setdefault(k, k)
        while self.parent[k] != k:
            self.parent[k] = self.parent[self.parent[k]]
            k = self.parent[k]
        return k

    def union(self, a: str, b: str):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def _contest_groups(recs: list[dict]) -> _Groups:
    g = _Groups()
    by_dated: dict[tuple, str] = {}
    by_old: dict[str, dict] = {}
    undated: dict[str, list[str]] = {}
    dated_names: dict[str, set] = {}
    for rec in recs:
        k = key(rec)
        g.find(k)
        # The old rule (title + provider + deadline, across sources) still holds.
        old = f"{norm(rec['title'])}|{norm(rec.get('provider', ''))}|{rec.get('apply_end') or ''}"
        if old in by_old and by_old[old]["source"] != rec["source"]:
            g.union(key(by_old[old]), k)
        by_old.setdefault(old, rec)
        end = rec.get("apply_end")
        for q in quoted_names(rec["title"]) if end else ():
            if ("q", q, end) in by_dated:
                g.union(by_dated[("q", q, end)], k)
            by_dated.setdefault(("q", q, end), k)
        name = contest_norm(rec["title"])
        if len(name) < MIN_CONTEST_KEY:
            continue
        if end:
            if (name, end) in by_dated:
                g.union(by_dated[(name, end)], k)
            by_dated.setdefault((name, end), k)
            dated_names.setdefault(name, set()).add(end)
        else:
            undated.setdefault(name, []).append(k)
    # No deadline on one side: join when the title matches exactly and only one dated listing has that title.
    for name, ks in undated.items():
        for k in ks[1:]:
            g.union(ks[0], k)
        ends = dated_names.get(name, set())
        if len(ends) == 1:
            g.union(by_dated[(name, next(iter(ends)))], ks[0])
    return g


def merge(previous: list[dict], fresh: list[dict], run_date: str) -> list[dict]:
    by_key = {key(r): r for r in previous}
    for rec in fresh:
        old = by_key.get(key(rec))
        rec["first_seen"] = old.get("first_seen", run_date) if old else run_date
        rec["last_seen"] = run_date
        by_key[key(rec)] = rec
    records = sorted(by_key.values(), key=lambda r: (r["source"], r["source_id"]))
    for rec in records:
        rec["status"] = status(rec)
        rec.pop("also_in", None)  # recomputed below; a record kept from an earlier run must not pile up links
        rec.pop("sources", None)

    # Contests: looser cross-site rule (strong title key + deadline), provider left out because
    # linkareer often names the agency instead of the host.
    contests = [r for r in records if r.get("type") == "contest"]
    groups = _contest_groups(contests)
    members: dict[str, list[dict]] = {}
    for rec in contests:
        members.setdefault(groups.find(key(rec)), []).append(rec)
    dropped: set[str] = set()
    for recs in members.values():
        if len(recs) < 2:
            continue
        recs.sort(key=lambda r: (tuple(-int(x) for x in _richness(r)), r["source"], r["source_id"]))
        kept, rest = recs[0], recs[1:]
        kept["also_in"] = [key(r) for r in rest]
        kept["sources"] = list(dict.fromkeys([kept["source"]] + [r["source"] for r in rest]))
        dropped |= {key(r) for r in rest}

    # Everything else: the same programme listed by two sources: keep one, remember the other.
    seen: dict[str, dict] = {}
    out = []
    for rec in records:
        if rec.get("type") == "contest":
            if key(rec) not in dropped:
                out.append(rec)
            continue
        dup = f"{norm(rec['title'])}|{norm(rec.get('provider', ''))}|{rec.get('apply_end') or ''}"
        if dup in seen and seen[dup]["source"] != rec["source"]:
            first = seen[dup]
            first.setdefault("also_in", []).append(key(rec))
            first["sources"] = list(dict.fromkeys(first.get("sources", [first["source"]]) + [rec["source"]]))
            continue
        seen[dup] = rec
        out.append(rec)
    # Drop items closed for more than 60 days so the file does not grow forever, except scholarships:
    # they recur every year, and the full catalog (with last year's dates) is what students plan with (D28).
    cutoff = (today() - dt.timedelta(days=60)).isoformat()
    return [r for r in out if r["source"] in KEEP_CLOSED
            or not (r["status"] == "closed" and (r.get("apply_end") or "9999") < cutoff)]
