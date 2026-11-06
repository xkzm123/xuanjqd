from __future__ import annotations

import pytest

from xuanjqd.models import Talk, demo_talks, parse_dt
from xuanjqd.qr import EYE_STYLES, MODULE_STYLES, QRStyle, ascii_art, render, to_svg
from xuanjqd.theme import THEMES

try:
    import zxingcpp

    HAS = True
except Exception:  # noqa: BLE001
    HAS = False


TALK = Talk(id=136991, company="浙江明贺钢管有限公司", title="2026 届校园宣讲会")


def test_render_card_and_plain():
    card = render(TALK, "hdu", QRStyle(scale=8))
    plain = render(TALK, "hdu", QRStyle(scale=8), plain=True)
    assert card.width > plain.width
    assert card.mode == "RGBA"
    assert plain.width == plain.height


@pytest.mark.skipif(not HAS, reason="需要 zxing-cpp")
@pytest.mark.parametrize("module", MODULE_STYLES)
def test_every_module_style_decodes(module):
    img = render(TALK, "hdu", QRStyle(scale=10, module=module, card=False))
    res = zxingcpp.read_barcode(img.convert("RGB"))
    assert res is not None and res.text == TALK.signin_url


@pytest.mark.skipif(not HAS, reason="需要 zxing-cpp")
@pytest.mark.parametrize("eye", EYE_STYLES)
def test_every_eye_style_decodes(eye):
    img = render(TALK, "hdu", QRStyle(scale=10, eye=eye, card=False))
    res = zxingcpp.read_barcode(img.convert("RGB"))
    assert res is not None and res.text == TALK.signin_url


@pytest.mark.skipif(not HAS, reason="需要 zxing-cpp")
def test_card_with_logo_still_decodes():
    import pathlib

    logo = pathlib.Path(__file__).parents[1] / "xuanjqd" / "assets" / "logo.png"
    if not logo.exists():
        pytest.skip("缺少 logo")
    img = render(TALK, "midnight", QRStyle(scale=10, logo=str(logo), gradient=True))
    res = zxingcpp.read_barcode(img.convert("RGB"))
    assert res is not None and res.text == TALK.signin_url


def test_ascii_art_shape():
    lines = ascii_art(TALK.signin_url, quiet=1)
    assert len(lines) > 10
    assert all(isinstance(x, str) for x in lines)
    assert any("█" in x or "▀" in x or "▄" in x for x in lines)


def test_svg_output():
    svg = to_svg(TALK, "forest", QRStyle())
    assert svg.lstrip().startswith("<svg")
    assert "path" in svg or "rect" in svg


def test_themes_all_render():
    for key in THEMES:
        img = render(TALK, key, QRStyle(scale=6, card=False))
        assert img.size[0] > 100


def test_demo_talks_count():
    assert len(demo_talks()) == 8
    assert all(t.id for t in demo_talks())


def test_parse_dt():
    assert parse_dt("2025-11-08 14:00").hour == 14
    assert parse_dt("2025/11/08").month == 11
    assert parse_dt("11-08") is not None
    assert parse_dt("不是时间") is None
