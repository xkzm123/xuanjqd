from __future__ import annotations

from datetime import datetime
from pathlib import Path

from xuanjqd import crawl

HTML = """
<ul class="css-con4">
<li><a target="_blank" href="/teachin/view/id/137342"><time>[11-09 18:30]</time>
<span class="css-360"><span class="status-text status-xin">新</span>厦门强力巨彩光电科技有限公司</span>
<span class="css-360">第6教研楼北116</span></a></li>
<li><a target="_blank" href="/teachin/view/id/137329"><time>[11-10 18:30]</time>
<span class="css-360">腾讯音乐娱乐科技（深圳）有限公司</span>
<span class="css-360">第6教研楼北114</span></a></li>
<li><a target="_blank" href="/jobfair/view/id/42112"><time>[11-06 14:30]</time>
<span class="css-360">某招聘会</span></a></li>
</ul>
"""


def test_parse_basic():
    talks = crawl.parse(HTML, today=datetime(2026, 11, 6))
    assert len(talks) == 2  # jobfair 不算宣讲会
    first = talks[0]
    assert first.id == 137342
    assert first.company == "厦门强力巨彩光电科技有限公司"
    assert first.location == "第6教研楼北116"
    assert first.status == "新"
    assert first.start_at == datetime(2026, 11, 9, 18, 30)
    assert first.url.endswith("/teachin/view/id/137342")


def test_parse_no_status_span():
    talks = crawl.parse(HTML, today=datetime(2026, 11, 6))
    second = talks[1]
    assert second.status == ""
    assert second.company.startswith("腾讯音乐")


def test_year_rollover():
    # 1 月的场次在 11 月看，应该算到明年
    html = HTML.replace("11-09 18:30", "01-05 09:00")
    talks = crawl.parse(html, today=datetime(2026, 11, 6))
    target = next(t for t in talks if t.id == 137342)
    assert target.start_at.year == 2027
    assert talks[-1].id == 137342  # 排到明年，自然在最后


def test_parse_empty():
    assert crawl.parse("<html><body>没有内容</body></html>") == []


def test_signin_url_from_talk():
    talks = crawl.parse(HTML, today=datetime(2026, 11, 6))
    assert "id=137342" in talks[0].signin_url
    assert "id_code=" in talks[0].signin_url


def test_cache_roundtrip(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(crawl, "DATA_DIR", tmp_path)
    monkeypatch.setattr(crawl, "CACHE_FILE", tmp_path / "talks.json")

    talks = crawl.parse(HTML, today=datetime(2026, 11, 6))
    crawl.save_cache(talks)
    back, when = crawl.load_cache()

    assert when is not None
    assert [t.id for t in back] == [137342, 137329]
    assert back[0].company == "厦门强力巨彩光电科技有限公司"
    assert back[0].status == "新"
