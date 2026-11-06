"""宣讲会数据模型 + CSV / JSON 导入导出。"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Sequence

from .codec import id_code, signin_url

WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

CSV_FIELDS = [
    "id",
    "company",
    "title",
    "date",
    "time",
    "end_time",
    "location",
    "url",
    "tags",
    "note",
]

_DT_FORMATS = [
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%m-%d %H:%M",
    "%m-%d",
]


def parse_dt(value: str | None, *, default_year: int | None = None) -> datetime | None:
    """尽量宽容地解析时间，解析不了就返回 None（绝不抛异常）。"""
    if not value:
        return None
    value = str(value).strip().replace("T", " ")
    if not value:
        return None
    for fmt in _DT_FORMATS:
        try:
            dt = datetime.strptime(value, fmt)
        except ValueError:
            continue
        if "%Y" not in fmt:
            dt = dt.replace(year=default_year or datetime.now().year)
        return dt
    return None


@dataclass
class Talk:
    """一场宣讲会。id 是唯一的硬信息，其余全是"让人看得懂"的装饰。"""

    id: int
    company: str = ""
    title: str = "校园宣讲会"
    start_at: datetime | None = None
    end_at: datetime | None = None
    location: str = ""
    url: str = ""
    tags: tuple[str, ...] = ()
    note: str = ""
    source: str = "range"

    # ---------- 派生字段 ----------
    @property
    def code(self) -> str:
        return id_code(self.id)

    @property
    def signin_url(self) -> str:
        return signin_url(self.id)

    @property
    def display_name(self) -> str:
        return self.company or f"宣讲会 #{self.id}"

    @property
    def date_label(self) -> str:
        if not self.start_at:
            return "待定"
        return f"{self.start_at:%m-%d} {WEEKDAYS[self.start_at.weekday()]}"

    @property
    def time_label(self) -> str:
        if not self.start_at:
            return ""
        if self.end_at:
            return f"{self.start_at:%H:%M}-{self.end_at:%H:%M}"
        return f"{self.start_at:%H:%M}"

    @property
    def sort_key(self) -> tuple[int, str]:
        return (0 if self.start_at else 1, self.start_at.isoformat() if self.start_at else "", )

    # ---------- 序列化 ----------
    def to_row(self) -> dict[str, str]:
        return {
            "id": str(self.id),
            "company": self.company,
            "title": self.title,
            "date": self.start_at.strftime("%Y-%m-%d") if self.start_at else "",
            "time": self.start_at.strftime("%H:%M") if self.start_at else "",
            "end_time": self.end_at.strftime("%H:%M") if self.end_at else "",
            "location": self.location,
            "url": self.url,
            "tags": "|".join(self.tags),
            "note": self.note,
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Talk":
        raw_id = row.get("id") or row.get("ID") or ""
        talk_id = int(str(raw_id).strip()) if str(raw_id).strip().isdigit() else 0
        start = parse_dt(row.get("date") and f"{row.get('date')} {row.get('time') or '00:00'}")
        if start is None:
            start = parse_dt(row.get("time"))
        end = None
        if start and row.get("end_time"):
            end = parse_dt(f"{start:%Y-%m-%d} {row['end_time']}")
        tags_raw = str(row.get("tags") or "")
        tags = tuple(t.strip() for t in tags_raw.replace("、", "|").replace(",", "|").split("|") if t.strip())
        return cls(
            id=talk_id,
            company=str(row.get("company") or "").strip(),
            title=str(row.get("title") or "校园宣讲会").strip(),
            start_at=start,
            end_at=end,
            location=str(row.get("location") or "").strip(),
            url=str(row.get("url") or "").strip(),
            tags=tags,
            note=str(row.get("note") or "").strip(),
            source="csv",
        )

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        d["tags"] = list(self.tags)
        d["start_at"] = self.start_at.isoformat() if self.start_at else None
        d["end_at"] = self.end_at.isoformat() if self.end_at else None
        d["code"] = self.code
        d["signin_url"] = self.signin_url
        return d


# ---------------- 批量构造 ----------------


def from_range(start: int, count: int, *, preset_base: str | None = None) -> list[Talk]:
    """老用法：给个起始 id，按顺序生成 count 个。"""
    if count <= 0:
        return []
    return [Talk(id=i, source="range") for i in range(start, start + count)]


def from_ids(ids: Iterable[int]) -> list[Talk]:
    seen: set[int] = set()
    out: list[Talk] = []
    for i in ids:
        if i in seen:
            continue
        seen.add(i)
        out.append(Talk(id=i, source="ids"))
    return out


def load_csv(path: str | Path) -> list[Talk]:
    path = Path(path)
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        talks = [Talk.from_row(r) for r in reader]
    return [t for t in talks if t.id]


def save_csv(talks: Sequence[Talk], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for t in talks:
            writer.writerow(t.to_row())
    return path


def save_json(talks: Sequence[Talk], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([t.to_json() for t in talks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def sort_talks(talks: Sequence[Talk]) -> list[Talk]:
    return sorted(talks, key=lambda t: (t.start_at or datetime.max, t.id))


# ---------------- 演示数据（截图/自测用，不碰任何真实接口） ----------------

_DEMO = [
    ("浙江明贺钢管有限公司", "2026 届校园宣讲会 · 机械/材料", 0, "14:00", "6 教中 325", ("机械", "材料")),
    ("杭州海康威视数字技术股份有限公司", "算法/嵌入式专场", 0, "18:30", "行政楼报告厅", ("大厂", "算法")),
    ("宁波均胜电子股份有限公司", "研发岗专场宣讲", 1, "10:00", "1 教 205", ("汽车电子",)),
    ("浙江大华技术股份有限公司", "2026 届校招宣讲会", 1, "15:30", "3 教 101", ("安防", "研发")),
    ("网易（杭州）网络有限公司", "游戏与前端专场", 2, "19:00", "图书馆报告厅", ("互联网", "游戏")),
    ("中电海康集团有限公司", "国企专场 · 电子信息", 3, "09:30", "2 教 401", ("国企", "电子")),
    ("杭州老板电器股份有限公司", "工业设计/供应链", 3, "14:00", "5 教 210", ("制造",)),
    ("浙江吉利控股集团有限公司", "智能驾驶专场", 4, "18:00", "行政楼报告厅", ("车企", "智驾")),
]


def demo_talks(start_id: int = 136991, base_date: datetime | None = None) -> list[Talk]:
    """生成 8 条假数据，用来跑通全流程 / 出截图。"""
    base = base_date or (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
    talks: list[Talk] = []
    for i, (company, title, day_offset, hhmm, place, tags) in enumerate(_DEMO):
        h, m = (int(x) for x in hhmm.split(":"))
        start = (base + timedelta(days=day_offset)).replace(hour=h, minute=m)
        talks.append(
            Talk(
                id=start_id + i,
                company=company,
                title=title,
                start_at=start,
                end_at=start + timedelta(hours=2),
                location=place,
                tags=tags,
                note="演示数据",
                source="demo",
            )
        )
    return talks
