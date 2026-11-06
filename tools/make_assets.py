"""生成 README 用的图片素材（一次性脚本，不参与运行）。

    python tools/make_assets.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from xuanjqd.models import Talk, demo_talks, sort_talks  # noqa: E402
from xuanjqd.qr import QRStyle, _font, render  # noqa: E402
from xuanjqd.theme import THEMES, get_theme  # noqa: E402

OUT = ROOT / "docs" / "images"
OUT.mkdir(parents=True, exist_ok=True)
TALKS = sort_talks(demo_talks())

MONO = "C:/Windows/Fonts/consola.ttf"
MONO_B = "C:/Windows/Fonts/consolab.ttf"
CJK = "C:/Windows/Fonts/msyh.ttc"
CJK_B = "C:/Windows/Fonts/msyhbd.ttc"


# ---------------------------------------------------------------- 文本工具


def _f(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except Exception:  # noqa: BLE001
        return _font(size)


def _fonts(size: int, bold: bool = False):
    return _f(MONO_B if bold else MONO, size), _f(CJK_B if bold else CJK, size)


def _pick(ch: str, mono, cjk):
    return cjk if ord(ch) > 0x2E7F else mono


def measure(text: str, size: int, bold: bool = False) -> float:
    mono, cjk = _fonts(size, bold)
    return sum(_pick(c, mono, cjk).getlength(c) for c in text)


def draw_text(d, x, y, text, size, color, bold=False):
    mono, cjk = _fonts(size, bold)
    for ch in text:
        f = _pick(ch, mono, cjk)
        d.text((x, y), ch, font=f, fill=color)
        x += f.getlength(ch)
    return x


def _label(draw, xy, text, size=22, color="#334155", bold=False):
    draw_text(draw, xy[0], xy[1], text, size, color, bold)


# ---------------------------------------------------------------- 图片加工


def frame(img: Image.Image, radius: int = 16, border: str = "#dfe5ef") -> Image.Image:
    """给截图加圆角 + 描边，README 里看起来整齐一点。"""
    img = img.convert("RGB")
    w, h = img.size
    pad = 2
    canvas = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    canvas.paste(img, (pad, pad), mask)
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle([pad, pad, w + pad - 1, h + pad - 1], radius=radius, outline=border, width=2)
    return canvas


def shot(src: Path, dst: Path, box: tuple[int, int, int, int]) -> Path:
    img = Image.open(src).crop(box)
    frame(img).save(dst, optimize=True)
    return dst


# ---------------------------------------------------------------- 素材


def style_wall() -> Path:
    theme = get_theme("hdu")
    mods = [("rounded", "圆角 rounded"), ("classy", "优雅 classy"), ("square", "方块 square"),
            ("dot", "圆点 dot"), ("diamond", "菱形 diamond")]
    eyes = [("rounded", "圆角 eye"), ("circle", "圆形 eye"), ("square", "方形 eye")]
    cell, pad, gap = 300, 40, 24
    cols = 5
    title_h, caption_h, row_gap = 46, 34, 26
    block_h = title_h + cell + caption_h
    W = pad * 2 + cols * cell + (cols - 1) * gap
    H = pad * 2 + block_h * 3 + row_gap * 2
    img = Image.new("RGB", (W, H), "#ffffff")
    d = ImageDraw.Draw(img)

    def block(title, items, top, mode):
        _label(d, (pad, top), title, 26, "#0f172a", bold=True)
        for i, (key, name) in enumerate(items):
            kw = {mode: key}
            q = render(Talk(id=136991), theme, QRStyle(scale=5, card=False, quiet=2, **kw))
            q = q.resize((cell, cell), Image.LANCZOS)
            x = pad + i * (cell + gap)
            img.paste(q, (x, top + title_h))
            _label(d, (x + 4, top + title_h + cell + 8), name, 18)

    block("模块形状", mods, pad, "module")
    block("定位点样式", eyes, pad + block_h + row_gap, "eye")

    top3 = pad + (block_h + row_gap) * 2
    _label(d, (pad, top3), "配色主题", 26, "#0f172a", bold=True)
    for i, (key, th) in enumerate(list(THEMES.items())[:5]):
        q = render(Talk(id=136991), th, QRStyle(scale=5, card=False, quiet=2, gradient=True))
        q = q.resize((cell, cell), Image.LANCZOS)
        x = pad + i * (cell + gap)
        img.paste(q, (x, top3 + title_h))
        _label(d, (x + 4, top3 + title_h + cell + 8), th.name, 18)

    p = OUT / "styles.png"
    img.save(p, optimize=True)
    return p


def terminal_png() -> Path:
    """手绘一张终端截图：rich 的 SVG 导出对中文对不齐，所以自己排版。"""
    W, H = 1180, 636
    bg, bar = "#12121c", "#1b1b28"
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=14, fill=bg)

    d.rounded_rectangle([0, 0, W, 46], radius=14, fill=bar)
    d.rectangle([0, 32, W, 46], fill=bar)
    for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        d.ellipse([20 + i * 22, 17, 32 + i * 22, 29], fill=c)
    draw_text(d, W / 2 - measure("xuanjqd gen — 终端", 14) / 2, 15, "xuanjqd gen — 终端", 14, "#8b93a7")

    x0, y = 34, 74
    size = 15

    x = draw_text(d, x0, y, "$ ", size, "#22c55e", True)
    draw_text(d, x, y, "xuanjqd gen --start 136991 -n 8 --gradient --sheet", size, "#e6edf7")
    y += 34

    cols = [(x0, "编号"), (x0 + 130, "时间"), (x0 + 330, "公司 / 宣讲会"), (x0 + 780, "地点")]
    for cx, name in cols:
        draw_text(d, cx, y, name, size, "#8b93a7", True)
    y += 30
    d.line([x0, y - 8, W - x0, y - 8], fill="#242438", width=1)

    for t in TALKS:
        draw_text(d, cols[0][0], y, f"#{t.id}", size, "#38bdf8")
        draw_text(d, cols[1][0], y, f"{t.date_label} {t.time_label}", size, "#c9d3e3")
        draw_text(d, cols[2][0], y, t.display_name, size, "#e6edf7")
        draw_text(d, cols[3][0], y, t.location, size, "#8b93a7")
        y += 28

    y += 12
    x = draw_text(d, x0, y, "● ", size, "#22c55e", True)
    x = draw_text(d, x, y, "完成 ", size, "#22c55e", True)
    draw_text(d, x, y, "1.9s", size, "#5b6478")
    y += 30

    tree = [
        ("二维码卡片", "8 张", "out/qr"),
        ("A4 拼版", "1 页", "out/sheet"),
        ("PDF", "", "out/签到码-A4.pdf"),
        ("长图", "", "out/wall.png"),
        ("网页画廊", "", "out/index.html"),
        ("清单", "", "out/codes.csv"),
        ("日历", "", "out/talks.ics"),
        ("扫码自检", "8/8", ""),
    ]
    for i, (name, count, path) in enumerate(tree):
        prefix = "└── " if i == len(tree) - 1 else "├── "
        x = draw_text(d, x0, y, prefix, size, "#3b4256")
        x = draw_text(d, x, y, name, size, "#c9d3e3")
        if count:
            x = draw_text(d, x + 14, y, count, size, "#5b6478")
        if path:
            draw_text(d, x + 16, y, "→ ", size, "#3b4256")
            draw_text(d, x + 34, y, path, size, "#38bdf8")
        y += 27

    y += 14
    draw_text(d, x0, y, "下一步：双击 out/index.html 预览；或运行 xuanjqd preview 打开可视化设计器。",
              size, "#5b6478")

    p = OUT / "terminal.png"
    img.save(p, optimize=True)
    return p


def hero() -> Path:
    """三张卡片拼一张横幅，README 顶部用。"""
    from PIL import ImageFilter

    cards = [render(TALKS[i], "hdu", QRStyle(scale=11, gradient=True)) for i in (0, 1, 4)]
    tw, gap, top = 400, 34, 70
    thumbs = []
    for c in cards:
        h = int(c.height * tw / c.width)
        thumbs.append(c.resize((tw, h), Image.LANCZOS))

    W = tw * 3 + gap * 2 + 160
    H = max(t.height for t in thumbs) + top * 2 + 40
    bg = Image.new("RGB", (W, H), "#f7f9fd")
    d = ImageDraw.Draw(bg)
    for y in range(H):
        t = y / max(1, H - 1)
        col = (int(247 - 8 * t), int(249 - 6 * t), int(253 - 4 * t))
        d.line([(0, y), (W, y)], fill=col)

    x = (W - (tw * 3 + gap * 2)) // 2
    for t in thumbs:
        shadow = Image.new("RGBA", (t.width + 80, t.height + 80), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle(
            [40, 40, 40 + t.width, 40 + t.height], radius=18, fill=(15, 23, 42, 46)
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(16))
        bg.paste(shadow, (x - 40, top - 30), shadow)
        bg.paste(t, (x, top), t if t.mode == "RGBA" else None)
        x += tw + gap

    p = OUT / "hero.png"
    bg.save(p, optimize=True)
    return p


def outputs() -> list[Path]:
    """从 out/ 里取生成结果，做成 README 展示图。"""
    made = []
    card = Image.open(ROOT / "out" / "qr" / "136991.png")
    card.save(OUT / "card.png", optimize=True)
    made.append(OUT / "card.png")

    s = Image.open(ROOT / "out" / "sheet" / "sheet-01.png")
    s.resize((1000, int(s.height * 1000 / s.width)), Image.LANCZOS).save(OUT / "sheet.png", optimize=True)
    made.append(OUT / "sheet.png")

    w = Image.open(ROOT / "out" / "wall.png")
    w.resize((620, int(w.height * 620 / w.width)), Image.LANCZOS).save(OUT / "wall.png", optimize=True)
    made.append(OUT / "wall.png")
    return made


def screenshots() -> list[Path]:
    made = []
    gal = ROOT / "_shot_gallery.png"
    if gal.exists():
        made.append(shot(gal, OUT / "gallery.png", (0, 110, 1912, 900)))
    des = ROOT / "_shot_designer.png"
    if des.exists():
        made.append(shot(des, OUT / "designer.png", (0, 110, 1912, 900)))
    return made


def main() -> None:
    for fn in (style_wall, terminal_png, hero):
        print("->", fn().relative_to(ROOT))
    for p in outputs() + screenshots():
        print("->", p.relative_to(ROOT))


if __name__ == "__main__":
    main()
