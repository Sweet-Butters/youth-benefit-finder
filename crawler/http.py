"""Polite HTTP helper for official APIs and files.

- The data.go.kr key comes only from the DATA_GO_KR_KEY environment variable (GitHub Secrets in CI,
  a local .env or shell variable when testing). It is never written to the repo or logged.
- Accepts the portal's Encoding or Decoding key: it is always unquoted once before use.
- Retries with back-off; one slow API must not stop the run.
- robots.txt is honoured for non-API web pages (same idea as korea-ai-contest-tracker).
"""
import os
import time
import urllib.parse
import urllib.robotparser

import requests

UA = "YouthBenefitFinder/0.1 (+https://github.com/Sweet-Butters/youth-benefit-finder)"
_session = requests.Session()
_session.headers["User-Agent"] = UA
_robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}


class MissingKey(Exception):
    pass


class RobotsDisallowed(Exception):
    pass


def data_go_kr_key() -> str:
    raw = os.environ.get("DATA_GO_KR_KEY", "").strip()
    if not raw:
        raise MissingKey("DATA_GO_KR_KEY is not set")
    return urllib.parse.unquote(raw)


def _redact(text: str) -> str:
    raw = os.environ.get("DATA_GO_KR_KEY", "")
    for k in {raw, urllib.parse.unquote(raw), urllib.parse.quote(urllib.parse.unquote(raw), safe="")} - {""}:
        text = text.replace(k, "***")
    return text


def get(url: str, params: dict | None = None, *, api_key: bool = False, retries: int = 3, timeout: int = 40) -> requests.Response:
    params = dict(params or {})
    if api_key:
        params["serviceKey"] = data_go_kr_key()
    else:
        _check_robots(url)
    last = None
    for attempt in range(retries):
        try:
            r = _session.get(url, params=params, timeout=timeout)
            if r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code}")
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(_redact(f"GET failed after {retries} tries: {url} ({last})"))


def _check_robots(url: str):
    p = urllib.parse.urlsplit(url)
    origin = f"{p.scheme}://{p.netloc}"
    if origin not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            res = _session.get(origin + "/robots.txt", timeout=15)
            if res.status_code == 200 and "<html" not in res.text[:500].lower():
                rp.parse(res.text.splitlines())
            else:
                rp = None
        except requests.RequestException:
            rp = None
        _robots[origin] = rp
    rp = _robots[origin]
    if rp is not None and not rp.can_fetch(UA, url):
        raise RobotsDisallowed(url)
