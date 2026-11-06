"""扫码自检：把生成的图再"扫"一遍，确认内容没被样式玩坏。

依赖 zxing-cpp（可选）。没装就返回 skipped，不影响主流程。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from PIL import Image

try:  # pragma: no cover - 取决于环境
    import zxingcpp

    HAS_ZXING = True
except Exception:  # noqa: BLE001
    zxingcpp = None  # type: ignore[assignment]
    HAS_ZXING = False


@dataclass
class VerifyResult:
    ok: bool
    text: str = ""
    reason: str = ""


def decode(image: Image.Image | str | Path) -> VerifyResult:
    if not HAS_ZXING:
        return VerifyResult(False, "", "skipped: 未安装 zxing-cpp")
    if not isinstance(image, Image.Image):
        image = Image.open(image)
    try:
        result = zxingcpp.read_barcode(image.convert("RGB"))
    except Exception as exc:  # noqa: BLE001
        return VerifyResult(False, "", f"decode error: {exc}")
    if result is None:
        return VerifyResult(False, "", "扫不出来")
    return VerifyResult(True, result.text)


def verify_payload(image: Image.Image | str | Path, expected: str) -> VerifyResult:
    res = decode(image)
    if not res.ok:
        return res
    if res.text.strip() != expected.strip():
        return VerifyResult(False, res.text, "内容不一致")
    return VerifyResult(True, res.text, "ok")


def verify_batch(items: Sequence[tuple[str, Image.Image | str | Path, str]]) -> list[tuple[str, VerifyResult]]:
    return [(name, verify_payload(img, expected)) for name, img, expected in items]
