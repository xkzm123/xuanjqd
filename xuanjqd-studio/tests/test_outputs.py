from __future__ import annotations

from pathlib import Path

from xuanjqd.gallery import write_gallery
from xuanjqd.ics import build_ics
from xuanjqd.layout import sheet, wall
from xuanjqd.models import Talk, demo_talks, load_csv, save_csv, save_json, sort_talks
from xuanjqd.qr import QRStyle


def test_csv_roundtrip(tmp_path: Path):
    talks = demo_talks()
    p = save_csv(talks, tmp_path / "codes.csv")
    back = load_csv(p)
    assert len(back) == len(talks)
    assert back[0].company == talks[0].company
    assert back[0].id == talks[0].id
    assert back[0].start_at is not None


def test_json_dump(tmp_path: Path):
    p = save_json(demo_talks()[:2], tmp_path / "m.json")
    text = p.read_text(encoding="utf-8")
    assert '"signin_url"' in text
    assert '"code"' in text


def test_sheet_pagination():
    talks = demo_talks()
    pages = sheet(talks, "hdu", QRStyle(scale=6))
    assert len(pages) == 1  # 8 张 < 12/页
    assert pages[0].size == (2480, 3508)


def test_sheet_two_pages():
    talks = [Talk(id=1000 + i) for i in range(13)]
    pages = sheet(talks, "hdu", QRStyle(scale=4))
    assert len(pages) == 2


def test_wall_size():
    img = wall(demo_talks()[:4], "hdu", QRStyle(scale=5), cols=2)
    assert img.width > 600 and img.height > 600


def test_gallery_html(tmp_path: Path):
    talks = sort_talks(demo_talks()[:3])
    p = write_gallery(tmp_path, talks, title="测试画廊")
    html = p.read_text(encoding="utf-8")
    assert "测试画廊" in html
    assert str(talks[0].id) in html
    assert "card" in html


def test_ics():
    ics = build_ics(demo_talks())
    assert ics.startswith("BEGIN:VCALENDAR")
    assert ics.count("BEGIN:VEVENT") == 8
    assert "END:VCALENDAR" in ics
    assert "\r\n" in ics
