"""输入解析：id 区间 / 指定 id / CSV / 演示数据，以及可选的在线探测。"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterable, Sequence

from .codec import extract_id
from .models import Talk, demo_talks, from_ids, from_range, load_csv


def resolve(
    *,
    start: int | None = None,
    count: int | None = None,
    ids: str | Iterable[int] | None = None,
    csv_path: str | Path | None = None,
    demo: bool = False,
    demo_count: int = 8,
) -> list[Talk]:
    """把命令行参数翻译成 Talk 列表。优先级：demo > csv > ids > 区间。"""
    if demo:
        return demo_talks()[: max(1, demo_count)]
    if csv_path:
        talks = load_csv(csv_path)
        if talks:
            return talks
    if ids:
        parsed: list[int] = []
        if isinstance(ids, str):
            for chunk in ids.replace("，", ",").split(","):
                chunk = chunk.strip()
                if not chunk:
                    continue
                got = extract_id(chunk)
                if got:
                    parsed.append(got)
        else:
            parsed = list(ids)
        if parsed:
            return from_ids(parsed)
    if start is not None and count:
        return from_range(start, count)
    return []


def merge_meta(existing: Sequence[Talk], incoming: Sequence[Talk]) -> list[Talk]:
    """用已有 CSV 里的公司/时间等元信息补全新生成的条目。"""
    by_id = {t.id: t for t in existing}
    out = []
    for t in incoming:
        old = by_id.get(t.id)
        if old and not t.company:
            t.company = old.company
            t.title = old.title
            t.start_at = t.start_at or old.start_at
            t.end_at = t.end_at or old.end_at
            t.location = old.location
            t.tags = old.tags
            t.note = old.note
        out.append(t)
    return out


def probe(talks: Sequence[Talk], *, timeout: float = 6.0, delay: float = 0.8) -> list[dict]:
    """可选：逐个请求签到 URL，看看哪些 id 还活着。

    默认不在主流程里跑；只发一次 GET，串行 + 间隔，不给对方添麻烦。
    """
    results = []
    for t in talks:
        item = {"id": t.id, "status": None, "ok": False, "note": ""}
        req = urllib.request.Request(
            t.signin_url,
            headers={"User-Agent": "xuanjqd/2.0 (personal schedule helper)"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                item["status"] = resp.status
                item["ok"] = 200 <= resp.status < 400
                item["note"] = resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as exc:
            item["status"] = exc.code
            item["note"] = str(exc.reason)
        except Exception as exc:  # noqa: BLE001
            item["note"] = f"{type(exc).__name__}: {exc}"
        results.append(item)
        time.sleep(delay)
    return results
