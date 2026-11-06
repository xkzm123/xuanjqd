#!/usr/bin/env python
"""命令行快捷入口。

    python main.py              # 打开本地界面（抓取 + 挑选 + 生成）
    python main.py --fetch      # 只抓一次宣讲会列表
    python main.py --gen        # 抓取并生成全部签到码
    python main.py --date 11-10 # 只生成某一天

等价于 `python -m xuanjqd ...`，完整参数见 `python -m xuanjqd gen --help`。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from xuanjqd.cli import app  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="宣讲会签到码")
    p.add_argument("--fetch", action="store_true", help="只抓取宣讲会列表")
    p.add_argument("--gen", action="store_true", help="抓取并生成全部签到码")
    p.add_argument("--date", "-d", default="", help="只生成某一天，如 11-10")
    p.add_argument("--start", "-s", type=int, default=0, help="起始编号（配合 --count 任意生成）")
    p.add_argument("--count", "-n", type=int, default=0, help="生成数量")
    p.add_argument("--out", "-o", default="out", help="输出目录")
    p.add_argument("--theme", "-t", default="hdu", help="配色主题")
    return p


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass

    args = build_parser().parse_args()

    if args.fetch:
        app(["fetch"])
        return

    if args.gen or args.date or (args.start and args.count):
        argv = ["gen", "--out", args.out, "--theme", args.theme]
        if args.date:
            argv += ["--date", args.date]
        if args.start and args.count:
            argv += ["--start", str(args.start), "--count", str(args.count)]
        app(argv)
        return

    app(["preview"])


if __name__ == "__main__":
    main()
