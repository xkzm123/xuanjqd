#!/usr/bin/env python
"""一键版入口（兼容老用法）。

    python main.py                          # 从 136991 开始生成 6 场，全套物料
    python main.py --start 136991 -n 8      # 指定区间
    python main.py --demo                   # 演示数据（出截图用）
    python main.py --legacy                 # 老行为：pic/ 下只放纯二维码

需要更细的控制请用 CLI：python -m xuanjqd gen --help
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console  # noqa: E402

from xuanjqd.cli import app  # noqa: E402
from xuanjqd.models import from_range, sort_talks  # noqa: E402
from xuanjqd.qr import classic_png  # noqa: E402

console = Console()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="宣讲会签到码批量生成")
    p.add_argument("--start", "-s", type=int, default=136991, help="起始 id")
    p.add_argument("--count", "-n", type=int, default=6, help="生成数量")
    p.add_argument("--out", "-o", default="out", help="输出目录")
    p.add_argument("--theme", "-t", default="hdu", help="配色主题")
    p.add_argument("--demo", action="store_true", help="使用演示数据")
    p.add_argument("--legacy", action="store_true", help="老行为：只输出 pic/ 纯二维码")
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

    if args.legacy:
        talks = sort_talks(from_range(args.start, args.count))
        pic = Path("pic")
        pic.mkdir(exist_ok=True)
        for t in talks:
            classic_png(t, pic / f"{t.id}.png")
            console.print(f"[green]OK[/green] {pic / f'{t.id}.png'}")
        console.print(f"[dim]共 {len(talks)} 张，已完成。[/dim]")
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
