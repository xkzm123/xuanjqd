"""排版：A4 拼版（可直接打印裁剪）、长图（发群/发朋友圈）、PDF 合并。"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw

from .models import Talk
from .qr import QRStyle, _font, hex2rgb, render
from .theme import Theme, get_theme

A4 = (2480, 3508)  # 300 dpi


def _fit(img: Image.Image, box_w: int, box_h: int) -> Image.Image:
    ratio = min(box_w / img.width, box_h / img.height, 1.0)
    if ratio >= 1.0:
        return img
    return img.resize((max(1, int(img.width * ratio)), max(1, int(img.height * ratio))), Image.LANCZOS)


def sheet(
    talks: Sequence[Talk],
    theme: Theme | str | None = None,
    style: QRStyle | None = None,
    *,
    cols: int = 3,
    rows: int = 4,
    margin: int = 80,
    gap: int = 36,
    title: str = "",
    dpi_scale: float = 1.0,
) -> list[Image.Image]:
    """把若干张卡片排成 A4 页面，带裁切辅助线。"""
    theme = get_theme(theme)
    style = style or QRStyle(scale=11)
    page_w, page_h = int(A4[0] * dpi_scale), int(A4[1] * dpi_scale)
    per_page = cols * rows
    pages: list[Image.Image] = []
    cards = [render(t, theme, style) for t in talks]

    for page_idx in range(0, max(1, len(cards)), per_page):
        chunk = cards[page_idx : page_idx + per_page]
        page = Image.new("RGB", (page_w, page_h), (255, 255, 255))
        draw = ImageDraw.Draw(page)
        cell_w = (page_w - margin * 2 - gap * (cols - 1)) / cols
        cell_h = (page_h - margin * 2 - gap * (rows - 1)) / rows

        for i, card in enumerate(chunk):
            r, c = divmod(i, cols)
            x0 = margin + c * (cell_w + gap)
            y0 = margin + r * (cell_h + gap)
            fitted = _fit(card, int(cell_w) - 10, int(cell_h) - 10)
            px = int(x0 + (cell_w - fitted.width) / 2)
            py = int(y0 + (cell_h - fitted.height) / 2)
            page.paste(fitted, (px, py), fitted if fitted.mode == "RGBA" else None)

            # 裁切线（浅灰十字）
            for cx in (x0, x0 + cell_w):
                for cy in (y0, y0 + cell_h):
                    draw.line([(cx - 12, cy), (cx + 12, cy)], fill=(210, 214, 222), width=2)
                    draw.line([(cx, cy - 12), (cx, cy + 12)], fill=(210, 214, 222), width=2)

        # 页脚
        f = _font(22)
        footer = title or "宣讲会签到码"
        total_pages = (len(cards) + per_page - 1) // per_page
        draw.text((margin, page_h - margin // 2 - 8), footer, font=f, fill=hex2rgb(theme.sub))
        label = f"{page_idx // per_page + 1} / {max(1, total_pages)}"
        draw.text((page_w - margin - 70, page_h - margin // 2 - 8), label, font=f, fill=hex2rgb(theme.sub))
        pages.append(page)
    return pages


def wall(
    talks: Sequence[Talk],
    theme: Theme | str | None = None,
    style: QRStyle | None = None,
    *,
    cols: int = 2,
    title: str = "本周宣讲会签到码",
    subtitle: str = "",
) -> Image.Image:
    """一张长图，适合发班级群 / 朋友圈。"""
    theme = get_theme(theme)
    style = style or QRStyle(scale=12)
    cards = [render(t, theme, style) for t in talks]
    if not cards:
        return Image.new("RGB", (800, 400), (255, 255, 255))

    cw = max(c.width for c in cards)
    ch = max(c.height for c in cards)
    pad = 60
    header = 200 if title else pad
    cols = max(1, min(cols, len(cards)))
    rows = (len(cards) + cols - 1) // cols
    gap = 36
    width = pad * 2 + cols * cw + (cols - 1) * gap
    height = header + rows * ch + (rows - 1) * gap + pad

    img = Image.new("RGB", (width, height), hex2rgb(theme.page))
    draw = ImageDraw.Draw(img)
    # 顶部渐变条
    for i in range(10):
        t = i / 9
        c1 = hex2rgb(theme.dark)
        c2 = hex2rgb(theme.dark2)
        col = tuple(int(c1[k] + (c2[k] - c1[k]) * t) for k in range(3))
        draw.rectangle([0, i * 4, width, i * 4 + 4], fill=col)

    if title:
        draw.text((pad, 62), title, font=_font(56, bold=True), fill=hex2rgb(theme.ink))
        if subtitle:
            draw.text((pad, 136), subtitle, font=_font(28), fill=hex2rgb(theme.sub))

    for i, card in enumerate(cards):
        r, c = divmod(i, cols)
        x = pad + c * (cw + gap) + (cw - card.width) // 2
        y = header + r * (ch + gap)
        img.paste(card, (x, y), card if card.mode == "RGBA" else None)

    return img


def save_pdf(pages: Sequence[Image.Image], path: str | Path, dpi: int = 300) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rgb = [p.convert("RGB") for p in pages]
    rgb[0].save(path, save_all=True, append_images=rgb[1:], resolution=dpi, format="PDF")
    return path


def save_pages(pages: Sequence[Image.Image], out_dir: str | Path, prefix: str = "sheet") -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, page in enumerate(pages, 1):
        p = out_dir / f"{prefix}-{i:02d}.png"
        page.save(p, optimize=True)
        paths.append(p)
    return paths


def png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
