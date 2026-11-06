"""学校/平台预设。

默认给杭电，其他学校只要补一条 (base, template) 就能用——
二维码里装的永远只是"一条 URL"，所以这个项目本质上是通用的。
"""

from __future__ import annotations

from dataclasses import dataclass

from .codec import DEFAULT_BASE, DEFAULT_TEMPLATE


@dataclass(frozen=True)
class Preset:
    key: str
    name: str
    base: str
    template: str = DEFAULT_TEMPLATE
    site: str = ""


PRESETS: dict[str, Preset] = {
    "hdu": Preset(
        key="hdu",
        name="杭州电子科技大学 · 24365 就业数智平台",
        base=DEFAULT_BASE,
        site="https://job.hdu.edu.cn/",
    ),
    "custom": Preset(
        key="custom",
        name="自定义平台",
        base="http://example.com/signin",
        template="{base}?id={id}&id_code={code}&signin=1",
    ),
}


def get_preset(key: str) -> Preset:
    try:
        return PRESETS[key.lower()]
    except KeyError as exc:  # pragma: no cover - 交互路径
        raise KeyError(f"未知预设 {key!r}，可选：{', '.join(PRESETS)}") from exc
