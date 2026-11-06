"""生成 README 用的图片素材（一次性脚本，不参与运行）。

    python tools/make_assets.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw  # noqa: E402

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


from PIL import ImageFont  # noqa: E402


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


def draw_segments(d, x, y, segs, size):
    for text, color, bold in segs:
        x = draw_text(d, x, y, text, size, color, bold)
    return x


# ---------------------------------------------------------------- 素材


def _label(draw, xy, text, size=22, color="#334155", bold=False):
    draw_text(draw, xy[0], xy[1], text, size, color, bold)


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


def before_after() -> Path:
    import qrcode

    old = qrcode.make(TALKS[0].signin_url, box_size=10, border=4).convert("RGB")
    old = old.resize((520, 520), Image.LANCZOS)
    new = render(TALKS[0], "hdu", QRStyle(scale=11, gradient=True))
    new = new.resize((int(new.width * 520 / new.height), 520), Image.LANCZOS)

    pad, top = 40, 78
    W = pad * 2 + old.width + 60 + new.width
    H = top + 520 + pad
    img = Image.new("RGB", (W, H), "#f6f8fc")
    d = ImageDraw.Draw(img)
    _label(d, (pad, 26), "v1 · 只有一张裸二维码", 24, "#64748b", bold=True)
    _label(d, (pad + old.width + 60, 26), "v2 · 卡片 / 信息 / 主题 / 自检", 24, "#0f172a", bold=True)
    img.paste(old, (pad, top))
    img.paste(new, (pad + old.width + 60, top), new if new.mode == 'RGBA' else None)
    p = OUT / "before-after.png"
    img.save(p, optimize=True)
    return p


def terminal_png() -> Path:
    """手绘一张终端截图：rich 的 SVG 导出对中文对不齐，所以自己排版。"""
    W, H = 1180, 636
    bg, bar = "#12121c", "#1b1b28"
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=14, fill=bg)

    # 标题栏
    d.rounded_rectangle([0, 0, W, 46], radius=14, fill=bar)
    d.rectangle([0, 32, W, 46], fill=bar)
    for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        d.ellipse([20 + i * 22, 17, 32 + i * 22, 29], fill=c)
    draw_text(d, W / 2 - measure("xuanjqd gen — 终端", 14) / 2, 15, "xuanjqd gen — 终端", 14, "#8b93a7")

    x0, y = 34, 74
    size = 15

    # 命令行
    x = draw_text(d, x0, y, "$ ", size, "#22c55e", True)
    x = draw_text(d, x, y, "xuanjqd gen --start 136991 -n 8 --gradient --sheet", size, "#e6edf7")
    y += 34

    # 表格
    cols = [(x0, "编号", "#8b93a7"), (x0 + 130, "时间", "#8b93a7"),
            (x0 + 330, "公司 / 宣讲会", "#8b93a7"), (x0 + 780, "地点", "#8b93a7")]
    for cx, name, color in cols:
        draw_text(d, cx, y, name, size, color, True)
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
        last = i == len(tree) - 1
        prefix = "└── " if last else "├── "
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


def crop_shot(src: Path, dst: Path, top: int = 110) -> Path | None:
    if not src.exists():
        return None
    img = Image.open(src)
    img.crop((0, top, img.width, img.height)).save(dst, optimize=True)
    return dst


def main() -> None:
    for fn in (style_wall, before_after, terminal_png):
        print("→", fn().relative_to(ROOT))
    for name in ("gallery", "designer"):
        src = ROOT / f"_shot_{name}.png"
        out = crop_shot(src, OUT / f"{name}.png")
        if out:
            print("→", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
