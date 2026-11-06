"""导出 .ics 日历：把宣讲会直接塞进手机日历，比截图靠谱。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Sequence

from .models import Talk

_FMT = "%Y%m%dT%H%M%S"


def _fold(line: str) -> str:
    """RFC5545 折行：每行不超过 75 字节。"""
    raw = line.encode("utf-8")
    if len(raw) <= 73:
        return line
    out, cur, size = [], "", 0
    for ch in line:
        b = len(ch.encode("utf-8"))
        if size + b > 72:
            out.append(cur)
            cur, size = ch, b
        else:
            cur += ch
            size += b
    out.append(cur)
    return "\r\n ".join(out)


def build_ics(talks: Sequence[Talk], *, calendar_name: str = "校园宣讲会") -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//xuanjqd//XuanJQD Studio//CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{calendar_name}",
    ]
    stamp = datetime.now().strftime(_FMT)
    for t in talks:
        if not t.start_at:
            continue
        start = t.start_at
        end = t.end_at or (start + timedelta(hours=2))
        desc = f"签到码编号：{t.id}\\n签到链接：{t.signin_url}"
        lines += [
            "BEGIN:VEVENT",
            f"UID:xuanjqd-{t.id}@local",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{start.strftime(_FMT)}",
            f"DTEND:{end.strftime(_FMT)}",
            _fold(f"SUMMARY:{t.display_name} · {t.title}"),
            _fold(f"LOCATION:{t.location or '待定'}"),
            _fold(f"DESCRIPTION:{desc}"),
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def save_ics(talks: Sequence[Talk], path: str | Path, *, calendar_name: str = "校园宣讲会") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_ics(talks, calendar_name=calendar_name), encoding="utf-8", newline="")
    return path
