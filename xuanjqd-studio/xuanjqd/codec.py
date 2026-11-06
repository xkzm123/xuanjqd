"""签到码编解码：id -> md5(id_code) -> 签到 URL。

这一层是整个项目唯一的"协议"知识，单独拆出来便于：
  * 换学校（--preset / --base / --template）
  * 单元测试
  * 被 Web 端、CLI、脚本共同复用
"""

from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qs, urlparse

# 杭电 24365 就业数智平台的签到二维码地址（原版逻辑，保持 100% 兼容）
DEFAULT_BASE = "http://job.hdu.edu.cn/teachin/qrcode"
DEFAULT_TEMPLATE = "{base}?id={id}&id_code={code}&signin=1"

_ID_RE = re.compile(r"(?:id=|/view/|/teachin/)(\d{4,9})")


def id_code(talk_id: int) -> str:
    """id 的 md5，就是平台要求的 id_code 参数。"""
    return hashlib.md5(str(int(talk_id)).encode("utf-8")).hexdigest()


def signin_url(
    talk_id: int,
    base: str = DEFAULT_BASE,
    template: str = DEFAULT_TEMPLATE,
) -> str:
    """拼出签到二维码里要装的那条 URL。"""
    return template.format(
        base=base.rstrip("?").rstrip("/"),
        id=int(talk_id),
        code=id_code(talk_id),
    )


def extract_id(text: str | int) -> int | None:
    """从任意粘进来的东西里抠出宣讲会 id。

    支持：
      * 纯数字         136995
      * 详情页链接      https://job.hdu.edu.cn/teachin/view?id=136995
      * 签到码链接      .../qrcode?id=136995&id_code=...&signin=1
    """
    if isinstance(text, int):
        return text
    text = (text or "").strip()
    if text.isdigit():
        return int(text)
    parsed = urlparse(text)
    qs = parse_qs(parsed.query)
    if "id" in qs and qs["id"][0].isdigit():
        return int(qs["id"][0])
    m = _ID_RE.search(text)
    return int(m.group(1)) if m else None


def verify_url(url: str, talk_id: int | None = None) -> bool:
    """校验一条签到 URL 的结构是否自洽（id 与 id_code 必须对得上）。"""
    qs = parse_qs(urlparse(url).query)
    if "id" not in qs or "id_code" not in qs:
        return False
    try:
        rid = int(qs["id"][0])
    except ValueError:
        return False
    if talk_id is not None and rid != int(talk_id):
        return False
    return qs["id_code"][0].lower() == id_code(rid)
