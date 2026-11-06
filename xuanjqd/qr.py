"""二维码渲染引擎 —— 本项目"好看"的部分全在这里。

设计目标
--------
1. **扫得出来**：默认 H 级纠错 + 4 模块静区，任何花哨样式都不破坏可读性；
2. **能上墙**：圆角模块、渐变、中心 logo、卡片式信息区，可以直接打印张贴；
3. **可验证**：渲染完可以用 zxing-cpp 反解回读，确认内容没被玩坏。
"""

from __future__ import annotations

import io
import math
import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import segno

from .codec import signin_url
from .models import Talk
from .theme import Theme, get_theme

# ---------------------------------------------------------------- 字体

_FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

_font_cache: dict[tuple[int, bool], ImageFont.FreeTypeFont] = {}


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]
    candidates = _FONT_CANDIDATES if bold else _FONT_CANDIDATES[1:] + _FONT_CANDIDATES[:1]
    for path in candidates:
        if os.path.exists(path):
            try:
                f = ImageFont.truetype(path, size)
                _font_cache[key] = f
                return f
            except OSError:
                continue
    f = ImageFont.load_default()
    _font_cache[key] = f  # type: ignore[assignment]
    return f


# ---------------------------------------------------------------- 颜色


def hex2rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def rgb2hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(c))) for c in rgb)


def lerp(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return tuple(int(round(a + (b - a) * t)) for a, b in zip(c1, c2))  # type: ignore[return-value]


# ---------------------------------------------------------------- 样式


@dataclass
class QRStyle:
    """一次渲染的全部开关。Web 设计器就是拿它当参数面板。"""

    module: str = "rounded"      # square | rounded | classy | dot | diamond
    eye: str = "rounded"         # square | rounded | circle
    scale: int = 12              # 每个模块多少像素
    quiet: int = 4               # 静区（模块数），标准是 4
    error: str = "h"             # 纠错等级 L/M/Q/H
    gradient: bool = False
    logo: str | None = None
    logo_ratio: float = 0.17     # logo 占二维码边长的比例
    card: bool = True            # 是否画卡片（标题/时间/编号）
    caption: bool = True         # 卡片底部信息
    shadow: bool = False
    frame: bool = True           # 卡片描边
    corner: float = 0.6          # 圆角系数
    page_no: str = ""            # 右下角小字，例如 "1/8"

    def merged(self, **kwargs: Any) -> "QRStyle":
        clean = {k: v for k, v in kwargs.items() if v is not None and hasattr(self, k)}
        return replace(self, **clean) if clean else self

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "eye": self.eye,
            "scale": self.scale,
            "quiet": self.quiet,
            "error": self.error,
            "gradient": self.gradient,
            "logo_ratio": self.logo_ratio,
            "card": self.card,
            "caption": self.caption,
            "shadow": self.shadow,
            "frame": self.frame,
        }


MODULE_STYLES = ["square", "rounded", "classy", "dot", "diamond"]
EYE_STYLES = ["square", "rounded", "circle"]


# ---------------------------------------------------------------- 几何工具


def _arc_points(cx: float, cy: float, r: float, a0: float, a1: float, steps: int = 6) -> list[tuple[float, float]]:
    return [
        (cx + r * math.cos(a0 + (a1 - a0) * i / steps), cy + r * math.sin(a0 + (a1 - a0) * i / steps))
        for i in range(steps + 1)
    ]


def _module_polygon(x: float, y: float, s: float, radii: tuple[float, float, float, float]) -> list[tuple[float, float]]:
    """一个模块的轮廓；四个角各自可以带圆角，从而实现"连体圆角"效果。"""
    tl, tr, br, bl = radii
    x1, y1 = x + s, y + s
    pts: list[tuple[float, float]] = []
    if tl > 0:
        pts.append((x, y + tl))
        pts.extend(_arc_points(x + tl, y + tl, tl, math.pi, math.pi * 1.5))
    else:
        pts.append((x, y))
    if tr > 0:
        pts.append((x1 - tr, y))
        pts.extend(_arc_points(x1 - tr, y + tr, tr, -math.pi / 2, 0))
    else:
        pts.append((x1, y))
    if br > 0:
        pts.append((x1, y1 - br))
        pts.extend(_arc_points(x1 - br, y1 - br, br, 0, math.pi / 2))
    else:
        pts.append((x1, y1))
    if bl > 0:
        pts.append((x + bl, y1))
        pts.extend(_arc_points(x + bl, y1 - bl, bl, math.pi / 2, math.pi))
    else:
        pts.append((x, y1))
    return pts


def _fit_text(draw: ImageDraw.ImageDraw, text: str, font, max_w: float) -> str:
    if not text:
        return ""
    if draw.textlength(text, font=font) <= max_w:
        return text
    while text and draw.textlength(text + "…", font=font) > max_w:
        text = text[:-1]
    return text + "…" if text else ""


# ---------------------------------------------------------------- 主渲染


def _matrix(payload: str, error: str) -> tuple[Any, int]:
    qr = segno.make(payload, error=error, boost_error=True)
    m = qr.matrix
    return m, len(m)


def _is_eye(x: int, y: int, n: int) -> bool:
    return (x < 7 and y < 7) or (x >= n - 7 and y < 7) or (x < 7 and y >= n - 7)


def _draw_eyes(draw: ImageDraw.ImageDraw, n: int, s: float, ox: float, oy: float, style: str, color, S: int = 1) -> None:
    """三个定位点单独画，才能做出圆角/圆形"眼睛"。坐标按超采样倍率放大。"""
    size = 7 * s * S
    positions = [(0, 0), (n - 7, 0), (0, n - 7)]
    for cx, cy in positions:
        x0 = (ox + cx * s) * S
        y0 = (oy + cy * s) * S
        if style == "circle":
            draw.ellipse([x0, y0, x0 + size, y0 + size], fill=color)
            pad = 1.0 * s * S
            draw.ellipse([x0 + pad, y0 + pad, x0 + size - pad, y0 + size - pad], fill=(255, 255, 255, 255))
            pad2 = 2.0 * s * S
            draw.ellipse([x0 + pad2, y0 + pad2, x0 + size - pad2, y0 + size - pad2], fill=color)
        else:
            rad = 0.0 if style == "square" else size * 0.3
            draw.rounded_rectangle([x0, y0, x0 + size, y0 + size], radius=rad, fill=color)
            draw.rounded_rectangle(
                [x0 + s * S, y0 + s * S, x0 + size - s * S, y0 + size - s * S],
                radius=max(0.0, rad - s * S * 0.35),
                fill=(255, 255, 255, 255),
            )
            draw.rounded_rectangle(
                [x0 + 2 * s * S, y0 + 2 * s * S, x0 + size - 2 * s * S, y0 + size - 2 * s * S],
                radius=max(0.0, rad - s * S * 0.6),
                fill=color,
            )


def _shadow(img: Image.Image, box, radius: float, blur: int = 18, alpha: int = 40) -> Image.Image:
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(box, radius=radius, fill=(15, 23, 42, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    return Image.alpha_composite(img, layer)


def render(
    talk: Talk,
    theme: Theme | str | None = None,
    style: QRStyle | None = None,
    *,
    plain: bool = False,
    width: int | None = None,
) -> Image.Image:
    """把一场宣讲会渲染成一张可打印的卡片（或纯二维码）。"""
    theme = get_theme(theme)
    style = style or QRStyle()
    payload = talk.signin_url

    m, n = _matrix(payload, style.error)
    s = float(style.scale)
    qr_px = n * s
    quiet = style.quiet * s
    S = 2  # 超采样，抗锯齿
    dark = hex2rgb(theme.dark)
    dark2 = hex2rgb(theme.dark2)

    if plain or not style.card:
        side = qr_px + quiet * 2
        img = Image.new("RGBA", (int(side * S), int(side * S)), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)
        ox = oy = quiet
        _paint_modules(draw, m, n, s, ox, oy, style, dark, dark2, S)
        _draw_eyes(draw, n, s, ox, oy, style.eye, _color_at(theme, 0.5), S)
        img = img.resize((int(side), int(side)), Image.LANCZOS)
        return _maybe_width(img, width)

    margin = quiet + 14
    header_h = 104.0
    footer_h = 96.0 if style.caption else 18.0
    card_w = qr_px + margin * 2
    card_h = header_h + qr_px + footer_h
    if style.caption:
        card_h += 6

    img = Image.new("RGBA", (int(card_w * S), int(card_h * S)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    box = [0, 0, card_w * S - 1, card_h * S - 1]
    if style.shadow:
        img = _shadow(img, box, 28 * S)
        draw = ImageDraw.Draw(img)

    draw.rounded_rectangle(box, radius=28 * S, fill=hex2rgb(theme.paper) + (255,))
    if style.frame:
        draw.rounded_rectangle(box, radius=28 * S, outline=hex2rgb(theme.accent) + (46,), width=max(1, int(1.4 * S)))

    # 顶部主题条
    draw.rounded_rectangle(
        [margin * S * 0.6, 26 * S, (margin * 0.6 + 46) * S, 30 * S],
        radius=2 * S,
        fill=hex2rgb(theme.accent) + (255,),
    )

    # 标题区
    f_company = _font(int(31 * S), bold=True)
    f_title = _font(int(19 * S))
    company = _fit_text(draw, talk.display_name, f_company, (card_w - margin * 2) * S)
    draw.text((margin * S, 40 * S), company, font=f_company, fill=hex2rgb(theme.ink) + (255,))
    sub = _fit_text(draw, talk.title, f_title, (card_w - margin * 2) * S)
    if sub:
        draw.text((margin * S, 78 * S), sub, font=f_title, fill=hex2rgb(theme.sub) + (255,))

    # 二维码
    qr_y = header_h
    _paint_modules(draw, m, n, s, margin, qr_y, style, dark, dark2, S)
    _draw_eyes(draw, n, s, margin, qr_y, style.eye, _color_at(theme, 0.5), S)

    if style.logo:
        _paste_logo(img, style.logo, margin, qr_y, qr_px, style.logo_ratio, S)

    # 底部信息
    if style.caption:
        y = qr_y + qr_px + 16
        draw.line(
            [(margin * S, y * S), ((card_w - margin) * S, y * S)],
            fill=hex2rgb(theme.accent) + (36,),
            width=max(1, int(S)),
        )
        f_meta = _font(int(21 * S), bold=True)
        f_sub = _font(int(17 * S))
        when = " · ".join(x for x in [talk.date_label, talk.time_label] if x)
        draw.text((margin * S, (y + 12) * S), when, font=f_meta, fill=hex2rgb(theme.ink) + (255,))
        if talk.location:
            draw.text((margin * S, (y + 42) * S), talk.location, font=f_sub, fill=hex2rgb(theme.sub) + (255,))

        # 编号徽章
        badge = f"#{talk.id}"
        f_badge = _font(int(16 * S), bold=True)
        bw = draw.textlength(badge, font=f_badge) + 20 * S
        bx1 = (card_w - margin) * S
        bx0 = bx1 - bw
        by0 = (y + 14) * S
        draw.rounded_rectangle(
            [bx0, by0, bx1, by0 + 26 * S],
            radius=13 * S,
            fill=hex2rgb(theme.accent) + (22,),
        )
        draw.text((bx0 + 10 * S, by0 + 5 * S), badge, font=f_badge, fill=hex2rgb(theme.accent) + (255,))

    if style.page_no:
        f_pg = _font(int(13 * S))
        draw.text(
            ((card_w - margin) * S - draw.textlength(style.page_no, font=f_pg), (card_h - 26) * S),
            style.page_no,
            font=f_pg,
            fill=hex2rgb(theme.sub) + (170,),
        )

    img = img.resize((int(card_w), int(card_h)), Image.LANCZOS)
    return _maybe_width(img, width)


def _maybe_width(img: Image.Image, width: int | None) -> Image.Image:
    if not width or img.width == width:
        return img
    h = round(img.height * width / img.width)
    return img.resize((width, h), Image.LANCZOS)


def _color_at(theme: Theme, t: float):
    return lerp(hex2rgb(theme.dark), hex2rgb(theme.dark2), t) + (255,)


def _paint_modules(draw, m, n, s, ox, oy, style, dark, dark2, S) -> None:
    gradient = style.gradient and dark != dark2
    denom = max(1, 2 * n - 2)

    def color_for(x: int, y: int):
        if not gradient:
            return dark + (255,)
        return lerp(dark, dark2, (x + y) / denom) + (255,)

    for y in range(n):
        row = m[y]
        for x in range(n):
            if not row[x] or _is_eye(x, y, n):
                continue
            px = (ox + x * s) * S
            py = (oy + y * s) * S
            size = s * S
            fill = color_for(x, y)
            if style.module == "dot":
                draw.ellipse([px, py, px + size, py + size], fill=fill)
                continue
            if style.module == "diamond":
                c = size / 2
                draw.polygon([(px + c, py), (px + size, py + c), (px + c, py + size), (px, py + c)], fill=fill)
                continue
            if style.module == "square":
                draw.rectangle([px, py, px + size, py + size], fill=fill)
                continue

            # rounded / classy：只在"外侧角"打圆，形成连体感
            k = 0.5 if style.module == "rounded" else 0.42
            r = s * S * k * style.corner
            up = m[y - 1][x] if y > 0 else 0
            down = m[y + 1][x] if y < n - 1 else 0
            left = m[y][x - 1] if x > 0 else 0
            right = m[y][x + 1] if x < n - 1 else 0
            tl = r if (not up and not left) else 0
            tr = r if (not up and not right) else 0
            br = r if (not down and not right) else 0
            bl = r if (not down and not left) else 0
            pts = _module_polygon(px, py, size, (tl, tr, br, bl))
            draw.polygon(pts, fill=fill)


def _paste_logo(img: Image.Image, logo_path: str, ox: float, oy: float, qr_px: float, ratio: float, S: int) -> None:
    try:
        logo = Image.open(logo_path).convert("RGBA")
    except (OSError, ValueError):
        return
    target = int(qr_px * ratio * S)
    logo.thumbnail((target, target), Image.LANCZOS)
    pad = int(target * 0.14)
    box = int(target + pad * 2)
    cx = int((ox + qr_px / 2) * S)
    cy = int((oy + qr_px / 2) * S)
    plate = Image.new("RGBA", (box, box), (0, 0, 0, 0))
    d = ImageDraw.Draw(plate)
    d.rounded_rectangle([0, 0, box - 1, box - 1], radius=int(box * 0.24), fill=(255, 255, 255, 255))
    plate.alpha_composite(logo, (pad + (target - logo.width) // 2, pad + (target - logo.height) // 2))
    img.alpha_composite(plate, (cx - box // 2, cy - box // 2))


# ---------------------------------------------------------------- 输出


def to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def save_png(img: Image.Image, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG", optimize=True)
    return path


def to_svg(talk: Talk, theme: Theme | str | None = None, style: QRStyle | None = None) -> str:
    """矢量版，印刷放大不糊。"""
    theme = get_theme(theme)
    style = style or QRStyle()
    qr = segno.make(talk.signin_url, error=style.error, boost_error=True)
    buf = io.BytesIO()
    qr.save(
        buf,
        kind="svg",
        scale=style.scale,
        border=style.quiet,
        dark=theme.dark,
        light=None,
        xmldecl=False,
        svgns=True,
        nl=True,
        omitsize=False,
    )
    return buf.getvalue().decode("utf-8")


def ascii_art(payload: str, *, quiet: int = 2, error: str = "h") -> list[str]:
    """终端里的二维码（半块字符），rich 上色也兼容。"""
    m, n = _matrix(payload, error)
    lines: list[str] = []
    blank = " " * (n + quiet * 2)
    for _ in range(quiet):
        lines.append(blank)
    for y in range(0, n, 2):
        row_top = m[y]
        row_bot = m[y + 1] if y + 1 < n else [0] * n
        chars = [" "] * quiet
        for x in range(n):
            top, bot = row_top[x], row_bot[x]
            chars.append("█" if top and bot else "▀" if top else "▄" if bot else " ")
        chars.extend([" "] * quiet)
        lines.append("".join(chars))
    for _ in range(quiet):
        lines.append(blank)
    return lines


def batch_render(talks: Iterable[Talk], theme, style: QRStyle, width: int | None = None) -> list[tuple[Talk, Image.Image]]:
    return [(t, render(t, theme, style, width=width)) for t in talks]
