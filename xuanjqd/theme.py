"""配色主题。

一个主题 = 一组颜色，QR 模块用 dark→dark2 做渐变，卡片用 paper 做底。
所有主题都保证"模块与背景对比度足够"，扫得出来是第一位的。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    key: str
    name: str
    dark: str          # 二维码主色（渐变起点）
    dark2: str         # 二维码渐变色终点
    paper: str         # 卡片底色
    ink: str           # 主文字
    sub: str           # 次要文字
    accent: str        # 点缀色（徽章/分隔线）
    page: str = "#f5f7fb"   # 画廊页面背景

    @property
    def gradient(self) -> tuple[str, str]:
        return (self.dark, self.dark2)


THEMES: dict[str, Theme] = {
    "hdu": Theme(
        key="hdu",
        name="杭电蓝",
        dark="#0b2f6b",
        dark2="#1f6feb",
        paper="#ffffff",
        ink="#0f172a",
        sub="#64748b",
        accent="#1f6feb",
        page="#eef3fb",
    ),
    "midnight": Theme(
        key="midnight",
        name="午夜靛",
        dark="#141433",
        dark2="#4f46e5",
        paper="#ffffff",
        ink="#111827",
        sub="#6b7280",
        accent="#7c3aed",
        page="#f3f2ff",
    ),
    "forest": Theme(
        key="forest",
        name="松林绿",
        dark="#083b2b",
        dark2="#0f8a5f",
        paper="#ffffff",
        ink="#0b1f17",
        sub="#5b7268",
        accent="#0f8a5f",
        page="#eef8f3",
    ),
    "sunset": Theme(
        key="sunset",
        name="落日橙",
        dark="#7a1f0f",
        dark2="#e2542a",
        paper="#ffffff",
        ink="#2b120a",
        sub="#8a6a5f",
        accent="#e2542a",
        page="#fdf1ec",
    ),
    "sakura": Theme(
        key="sakura",
        name="樱花粉",
        dark="#5b1f3a",
        dark2="#d6477e",
        paper="#ffffff",
        ink="#2a1020",
        sub="#8d6b7c",
        accent="#d6477e",
        page="#fdf0f5",
    ),
    "mono": Theme(
        key="mono",
        name="极简黑白",
        dark="#111111",
        dark2="#111111",
        paper="#ffffff",
        ink="#000000",
        sub="#6b7280",
        accent="#111111",
        page="#f4f4f5",
    ),
}

DEFAULT_THEME = "hdu"


def get_theme(name: str | Theme | None) -> Theme:
    if isinstance(name, Theme):
        return name
    return THEMES.get((name or DEFAULT_THEME).lower(), THEMES[DEFAULT_THEME])


def theme_names() -> list[str]:
    return list(THEMES)
