"""Shared helpers for the contest-listing sources (crawler/sources/contest_*.py).

The listing sites' terms forbid republishing their posts, so a contest keeps only facts from the list:
title, host (주최), the site's own detail URL, application period, category and the eligibility words.
Never the description body, posters or images. Same rule as korea-ai-contest-tracker ("title + link only").

- robots.txt: every request goes through crawler.http's robots check (RobotsDisallowed), re-read each run.
- Rate limit: at least `min_interval_sec` (config/contests.json) between requests to the same host.
- Formats are made the same on every site so merge.py can fold one contest listed on several sites into one:
  title without site badges, provider = the first host without legal-form words ((주), 사단법인, ...),
  dates as YYYY-MM-DD. All hosts stay in extra["hosts"] for the detail page.
"""
import datetime as dt
import html
import json
import re
import time
import urllib.parse
import urllib.robotparser
from pathlib import Path

import requests

from . import http
from .model import Item
from .util import KST, regions_from_text, today

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config" / "contests.json").read_text(encoding="utf-8"))
_CATALOG = ROOT / "data" / "processed" / "catalog.json"
_last_hit: dict[str, float] = {}


def label(site: str) -> str:
    return CONFIG["sites"][site]["label"]


def max_pages(site: str) -> int:
    return int(CONFIG["sites"][site].get("max_pages", 40))


# ---------------------------------------------------------------------------
# HTTP: robots.txt through crawler.http, plus a per-host pause.

def _throttle(url: str):
    host = urllib.parse.urlsplit(url).netloc
    wait = _last_hit.get(host, 0) + float(CONFIG.get("min_interval_sec", 1.0)) - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_hit[host] = time.monotonic()


def _prime_robots_unverified(url: str):
    """For a site whose TLS chain is incomplete (올콘): read its robots.txt without verification into
    crawler.http's cache, so the normal check still applies instead of silently allowing everything."""
    p = urllib.parse.urlsplit(url)
    origin = f"{p.scheme}://{p.netloc}"
    if origin in http._robots:
        return
    rp = urllib.robotparser.RobotFileParser()
    try:
        res = http._session.get(origin + "/robots.txt", timeout=15, verify=False)
        if res.status_code == 200 and "<html" not in res.text[:500].lower():
            rp.parse(res.text.splitlines())
        else:
            rp = None
    except requests.RequestException:
        rp = None
    http._robots[origin] = rp


def get(url: str, params: dict | None = None) -> requests.Response:
    """GET through crawler.http.get (robots.txt checked there; RobotsDisallowed propagates)."""
    _throttle(url)
    return http.get(url, params)


def post(url: str, *, data=None, headers: dict | None = None, verify: bool = True, retries: int = 3) -> requests.Response:
    """POST for the sites whose list is a JSON endpoint. robots.txt is checked the same way as http.get."""
    if not verify:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        _prime_robots_unverified(url)
    http._check_robots(url)
    last = None
    for attempt in range(retries):
        _throttle(url)
        try:
            r = http._session.post(url, data=data, headers=headers or {}, timeout=40, verify=verify)
            if r.status_code >= 500 or r.status_code == 429:
                raise requests.HTTPError(str(r.status_code))
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"POST failed after {retries} tries: {url} ({last})")


# ---------------------------------------------------------------------------
# Text and dates.

def clean(s) -> str:
    if s is None:
        return ""
    s = re.sub(r"<[^>]+>", " ", str(s))
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


_BADGE = re.compile(r"\s+(SPECIAL|신규|IDEA|NEW|HOT|BEST|추천)(?=\s|$)")


def clean_title(s) -> str:
    t = _BADGE.sub("", clean(s))
    return t.strip(" -·|")


_LEGAL = re.compile(r"\(\s*(주|사|재|유|사단|재단|학)\s*\)|㈜|㈔|㈕|주식회사|유한회사|사단법인|재단법인|학교법인|사회적협동조합")


def split_hosts(raw) -> list[str]:
    """'주최: (주)A, 사단법인 B / C' -> ['A', 'B', 'C'] (label and legal-form words dropped, order kept)."""
    out = []
    for part in re.split(r"\s*(?:,|/|·|•|ㆍ|、|\|)\s*", clean(raw)):
        part = re.sub(r"^\s*(주최사?|주관|후원)\s*[:：.]?\s*|\s+(주최|주관)$", "", part)
        part = re.sub(r"^\s*\(?\s*(주|사|재)\s*\)\s*", "", part)   # '사)한국민화협회', '주) 메타크래프트'
        p = re.sub(r"\s+", " ", _LEGAL.sub(" ", part)).strip(" .-")
        if p and p not in out:
            out.append(p)
    return out


def truncated(s: str) -> bool:
    return s.rstrip().endswith(("…", "..."))


def ymd(s) -> str | None:
    m = re.search(r"(20\d\d)[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})", str(s or ""))
    if not m:
        return None
    try:
        return dt.date(*map(int, m.groups())).isoformat()
    except ValueError:
        return None


def from_dday(text: str | None, minus_one: bool = False) -> str | None:
    """'D-12' -> today + 12 days (minus one day for sites that count the deadline itself); 'D-day' -> today."""
    if not text:
        return None
    base = today()
    m = re.search(r"D\s*-\s*(\d+)", text, re.I)
    if m:
        return (base + dt.timedelta(days=int(m.group(1)) - (1 if minus_one else 0))).isoformat()
    if re.search(r"D\s*-?\s*day|오늘", text, re.I):
        return base.isoformat()
    return None


def from_epoch_ms(v) -> str | None:
    if not v:
        return None
    return dt.datetime.fromtimestamp(int(v) / 1000, KST).date().isoformat()


# ---------------------------------------------------------------------------
# Eligibility and fields.

def tokens(target) -> list[str]:
    """'누구나 , 중학생 / 고등학생, 해당자 ▶' -> ['누구나', '중학생', '고등학생', '해당자']."""
    text = clean(" , ".join(target) if isinstance(target, (list, tuple)) else target)
    return [t.strip(" ▶>") for t in re.split(r"\s*[,/·•ㆍ]\s*", text) if t.strip(" ▶>")]


_NEUTRAL = {"기타", "해당자", "지역 제한", "지역제한"}
_NOT_YOUTH = {w for ws in CONFIG["not_youth_only_words"].values() for w in ws}
_OPEN = [w.replace(" ", "") for w in CONFIG["open_to_all_words"]]


def not_for_youth(toks: list[str]) -> bool:
    """Every named target is an organisation, young children or adults only (기업, 초등학생, 교사...)."""
    named = [t for t in toks if t not in _NEUTRAL]
    return bool(named) and all(any(w == t or (len(w) > 1 and t.startswith(w)) for w in _NOT_YOUTH) for t in named)


def open_to_all(toks: list[str]) -> bool:
    return any(t.replace(" ", "") in _OPEN for t in toks)


def _catalog_words() -> dict[str, list[str]]:
    try:
        cat = json.loads(_CATALOG.read_text(encoding="utf-8"))
        return {f["id"]: list(f.get("benefit_words") or []) for f in cat.get("fields", [])}
    except (OSError, ValueError):
        return {}


_FIELD_WORDS = _catalog_words()
_MAP = CONFIG["category_fields"]


def _has(word: str, text: str) -> bool:
    if re.fullmatch(r"[A-Za-z]+", word):
        return re.search(rf"(?<![A-Za-z]){re.escape(word)}(?![A-Za-z])", text) is not None
    return word in text


def fields_for(categories: list[str], title: str) -> list[str]:
    """Catalog field ids a contest's categories clearly map to.

    Each category label is split into parts ('문학/글/시나리오' -> 문학, 글, 시나리오); a part maps when it is one
    of the field's words. A label that maps to several fields (콘테스트코리아's '요리•뷰티•배우•오디션') is a
    bucket: only the fields the title also names are kept. More than `max_fields_without_title_match` fields
    overall (a host ticked every box) are likewise trimmed to the ones the title names.
    """
    def confirmed(fid: str) -> bool:
        words = next((m["words"] for m in _MAP if m["field"] == fid), []) + _FIELD_WORDS.get(fid, [])
        return any(len(w) > 1 and _has(w, title) for w in words)

    out: list[str] = []
    for cat in categories:
        if cat.startswith("기타"):   # '기타(예체능, e스포츠 등)' is a catch-all, not a field
            continue
        parts = [p for p in re.split(r"\s*[/·•ㆍ,]\s*|\s+", cat) if p]
        fs = [m["field"] for m in _MAP if any(_has(w, p) if len(w) > 1 else w == p for p in parts for w in m["words"])]
        fs = list(dict.fromkeys(fs))
        if len(fs) > 1:
            fs = [f for f in fs if confirmed(f)]
        out += [f for f in fs if f not in out]
    if len(out) > int(CONFIG.get("max_fields_without_title_match", 2)):
        out = [f for f in out if confirmed(f)]
    return out


def category_tag(cat: str) -> str:
    return "contest:" + re.sub(r"\s*[•·ㆍ]\s*", "/", clean(cat)).replace(" ", "")


# ---------------------------------------------------------------------------

def make_item(site: str, source_id, *, title, host, url: str, apply_start=None, apply_end=None,
              categories: list[str] | None = None, target="", note: str = "", extra: dict | None = None) -> Item | None:
    """One contest as an Item, or None when it is not for young people (organisations, children, adults only)
    or has no title or link. `note` is the site's extra eligibility line (e.g. 씽굿 '경기도 소재 대학 재학생'):
    it is added to target_text and a province it names becomes the region."""
    title = clean_title(title)
    if not title or not url:
        return None
    toks = tokens(target)
    if not_for_youth(toks):
        return None
    hosts = split_hosts(host)
    cats = [clean(c) for c in (categories or []) if clean(c)]
    fields = fields_for(cats, title)
    tags = ["contest"] + [category_tag(c) for c in cats] + [f"field:{f}" for f in fields]
    if open_to_all(toks):
        tags.append("open_to_all")
    note = clean(note)
    regions = regions_from_text(note) if note else []
    region_limited = any(t in ("지역 제한", "지역제한") for t in toks)
    if region_limited and not regions:
        tags.append("region_limited")   # the site says 지역 제한 but not where: the board shows "지역 제한", not 전국
    x = {"site": label(site), "hosts": hosts}
    if cats:
        x["category"] = " · ".join(cats)
    x.update(extra or {})
    return Item(
        source=site,
        source_id=str(source_id),
        type="contest",
        title=title,
        provider=hosts[0] if hosts else "",
        url=url,
        apply_start=apply_start,
        apply_end=apply_end,
        regions=regions or ([] if region_limited else ["all"]),
        target_text=", ".join(toks) + (f" ({note})" if note else ""),
        tags=list(dict.fromkeys(tags)),
        extra=x,
    )
