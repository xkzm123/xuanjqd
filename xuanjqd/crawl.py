"""从学校就业网抓宣讲会。

公开面（不需要登录）只有首页的「校园宣讲会」栏目，一次给出最近的 10 场，
带编号、时间、公司、地点 —— 正好够生成签到码。

如果以后有账号，把 Cookie 传给 `crawl(cookie=...)` 就能抓完整的列表页，
解析逻辑复用同一套。
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

from .models import Talk

BASE = "https://job.hdu.edu.cn"
HOME_URL = f"{BASE}/default/index/teachin"
LIST_URL = f"{BASE}/teachin"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

DATA_DIR = Path("data")
CACHE_FILE = DATA_DIR / "talks.json"

_ITEM_RE = re.compile(
    r'<li>\s*<a[^>]*href="(?:https?://[^"]*)?/teachin/view/id/(\d+)"[^>]*>(.*?)</a>\s*</li>',
    re.S,
)
_TIME_RE = re.compile(r"<time>\s*\[([^\]]+)\]\s*</time>")
_SPAN_RE = re.compile(r'<span class="css-360">(.*?)</span>', re.S)
_STATUS_RE = re.compile(r'<span class="status-text[^"]*">(.*?)</span>', re.S)
_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return _TAG_RE.sub("", text).replace("&nbsp;", " ").strip()


def _parse_dt(raw: str, *, today: datetime | None = None) -> datetime | None:
    """首页给的是 `11-09 18:30`，没有年份，按"最近的将来"补全。"""
    raw = raw.strip()
    today = today or datetime.now()
    for fmt in ("%m-%d %H:%M", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(raw, fmt)
        except ValueError:
            continue
        if "%Y" not in fmt:
            dt = dt.replace(year=today.year)
            if dt < today - timedelta(days=180):
                dt = dt.replace(year=today.year + 1)
        return dt
    return None


def parse(html: str, *, today: datetime | None = None) -> list[Talk]:
    """把首页/列表页里的宣讲会条目解析成 Talk。"""
    talks: list[Talk] = []
    seen: set[int] = set()
    for tid, body in _ITEM_RE.findall(html):
        talk_id = int(tid)
        if talk_id in seen:
            continue
        seen.add(talk_id)

        t = _TIME_RE.search(body)
        start = _parse_dt(t.group(1), today=today) if t else None

        status = _STATUS_RE.search(body)
        body_wo = _STATUS_RE.sub("", _TIME_RE.sub("", body))
        spans = [_clean(s) for s in _SPAN_RE.findall(body_wo)]
        spans = [s for s in spans if s]

        company = spans[0] if spans else f"宣讲会 #{talk_id}"
        location = spans[1] if len(spans) > 1 else ""

        talks.append(
            Talk(
                id=talk_id,
                company=company,
                title="校园宣讲会",
                start_at=start,
                location=location,
                url=f"{BASE}/teachin/view/id/{talk_id}",
                status=_clean(status.group(1)) if status else "",
                source="hdu",
            )
        )
    talks.sort(key=lambda x: (x.start_at or datetime.max, x.id))
    return talks


def fetch_html(url: str = HOME_URL, *, cookie: str = "", timeout: float = 20.0) -> str:
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": BASE + "/",
    }
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    for enc in ("utf-8", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def crawl(*, cookie: str = "", html: str | None = None, url: str | None = None) -> list[Talk]:
    """抓一次。html 参数可以直接喂一段保存下来的页面，方便离线调试。"""
    if html is None:
        target = url or (LIST_URL if cookie else HOME_URL)
        html = fetch_html(target, cookie=cookie)
    return parse(html)


# ---------------------------------------------------------------- 缓存


def save_cache(talks: Iterable[Talk], *, source: str = "hdu") -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": source,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(list(talks)),
        "talks": [t.to_json() for t in talks],
    }
    CACHE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return CACHE_FILE


def load_cache() -> tuple[list[Talk], datetime | None]:
    if not CACHE_FILE.exists():
        return [], None
    try:
        payload = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [], None
    talks = [Talk.from_json(item) for item in payload.get("talks", [])]
    fetched = payload.get("fetched_at")
    when = datetime.fromisoformat(fetched) if fetched else None
    return talks, when


@dataclass
class CrawlResult:
    talks: list[Talk]
    fetched_at: datetime
    source: str
    ok: bool = True
    error: str = ""
