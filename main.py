#!/usr/bin/env python
"""命令行快捷入口。

    python main.py                 # 从 136991 开始生成 6 场，全套物料
    python main.py --start 136991 -n 8
    python main.py --demo          # 演示数据
    python main.py --web           # 直接打开可视化设计器

等价于 `python -m xuanjqd ...`，参数见 `python -m xuanjqd gen --help`。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from xuanjqd.cli import app  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="宣讲会签到码批量生成")
    p.add_argument("--start", "-s", type=int, default=136991, help="起始 id")
    p.add_argument("--count", "-n", type=int, default=6, help="生成数量")
    p.add_argument("--out", "-o", default="out", help="输出目录")
    p.add_argument("--theme", "-t", default="hdu", help="配色主题")
    p.add_argument("--demo", action="store_true", help="使用演示数据")
    p.add_argument("--web", action="store_true", help="打开可视化设计器")
    p.add_argument("--logo", default="", help="中心 logo 路径")
    p.add_argument("--gradient", action="store_true", help="渐变填充")
    return p


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    args = build_parser().parse_args()

    if args.web:
        app(["preview"])
        return

    argv = ["gen", "--start", str(args.start), "-n", str(args.count),
            "--out", args.out, "--theme", args.theme]
    if args.demo:
        argv.append("--demo")
    if args.gradient:
        argv.append("--gradient")
    if args.logo:
        argv += ["--logo", args.logo]
    app(argv)


if __name__ == "__main__":
    main()
