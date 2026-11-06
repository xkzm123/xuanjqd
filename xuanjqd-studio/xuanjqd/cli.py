"""命令行入口：`xuanjqd gen` 一条命令出全套物料。"""

from __future__ import annotations

import json
import shutil
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from . import __version__
from .codec import signin_url
from .gallery import write_gallery
from .layout import save_pages, save_pdf, sheet, wall
from .models import Talk, demo_talks, save_csv, save_json, sort_talks
from .qr import MODULE_STYLES, EYE_STYLES, QRStyle, ascii_art, classic_png, render, save_png, to_svg
from .sources import merge_meta, probe, resolve
from .theme import THEMES, get_theme, theme_names
from .verify import HAS_ZXING, verify_payload

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="宣讲会签到码工坊 · 批量生成 / 可视化设计 / A4 拼版 / 扫码自检",
)
console = Console(highlight=False, emoji=False)

BANNER = r"""
 __  __ _   _    _    _   _      ___  ___  ____
 \ \/ /| | | |  / \  | \ | |    / _ \|  _ \|  _ \
  \  / | | | | / _ \ |  \| |   | | | | | | | | | |
  /  \ | |_| |/ ___ \| |\  |   | |_| | |_| | |_| |
 /_/\_\ \___//_/   \_\_| \_|    \__\_\___/|____/
"""


def _utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass


def _style(**kw) -> QRStyle:
    clean = {k: v for k, v in kw.items() if v is not None}
    return QRStyle(**clean)


def _summary_table(talks: list[Talk]) -> Table:
    table = Table(box=None, pad_edge=False, show_header=True, header_style="bold")
    table.add_column("编号", style="cyan", no_wrap=True)
    table.add_column("时间", no_wrap=True)
    table.add_column("公司 / 宣讲会", overflow="ellipsis", max_width=42)
    table.add_column("地点", overflow="ellipsis", max_width=18)
    for t in talks:
        table.add_row(
            f"#{t.id}",
            f"{t.date_label} {t.time_label}".strip() or "待定",
            t.display_name,
            t.location or "—",
        )
    return table


def _render_all(
    talks: list[Talk],
    *,
    out: Path,
    theme_key: str,
    style: QRStyle,
    want_sheet: bool,
    want_pdf: bool,
    want_wall: bool,
    want_svg: bool,
    want_ics: bool,
    want_zip: bool,
    clean: bool,
    quiet: bool,
    verify: bool,
    title: str,
) -> dict:
    theme = get_theme(theme_key)
    out.mkdir(parents=True, exist_ok=True)
    qr_dir = out / "qr"
    if clean and qr_dir.exists():
        shutil.rmtree(qr_dir)
    qr_dir.mkdir(parents=True, exist_ok=True)

    steps = 4 + int(want_sheet) + int(want_wall) + int(want_svg) + int(want_ics) + int(want_zip)
    result: dict = {"count": len(talks), "out": str(out), "qr": [], "errors": [], "verified": 0}

    progress = Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=28, style="grey35", complete_style="cyan"),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
        transient=not quiet,
        disable=quiet,
    )

    with progress:
        task = progress.add_task("渲染卡片", total=len(talks))
        for t in talks:
            try:
                img = render(t, theme, style)
                path = save_png(img, qr_dir / f"{t.id}.png")
                result["qr"].append(str(path))
                if verify:
                    v = verify_payload(img, t.signin_url)
                    if v.ok:
                        result["verified"] += 1
                    else:
                        result["errors"].append(f"#{t.id} 扫码校验失败：{v.reason}")
            except Exception as exc:  # noqa: BLE001
                result["errors"].append(f"#{t.id} 渲染失败：{exc}")
            progress.advance(task)

        if want_svg:
            svg_dir = out / "svg"
            svg_dir.mkdir(parents=True, exist_ok=True)
            st = progress.add_task("导出 SVG", total=len(talks))
            for t in talks:
                (svg_dir / f"{t.id}.svg").write_text(to_svg(t, theme, style), encoding="utf-8")
                progress.advance(st)

        if want_sheet:
            st = progress.add_task("A4 拼版", total=1)
            pages = sheet(
                talks,
                theme,
                _style(scale=11, module=style.module, eye=style.eye, gradient=style.gradient,
                       logo=style.logo, logo_ratio=style.logo_ratio),
                title=title,
            )
            sheet_dir = out / "sheet"
            result["sheet"] = [str(p) for p in save_pages(pages, sheet_dir)]
            if want_pdf:
                result["pdf"] = str(save_pdf(pages, out / "签到码-A4.pdf"))
            progress.advance(st)

        if want_wall:
            st = progress.add_task("长图", total=1)
            img = wall(talks, theme, style, cols=2 if len(talks) > 1 else 1, title=title)
            result["wall"] = str(save_png(img, out / "wall.png"))
            progress.advance(st)

        st = progress.add_task("生成画廊", total=1)
        result["gallery"] = str(write_gallery(out, talks, title=title, theme=theme))
        progress.advance(st)

        st = progress.add_task("导出清单", total=1)
        result["csv"] = str(save_csv(talks, out / "codes.csv"))
        save_json(talks, out / "manifest.json")
        progress.advance(st)

        if want_ics:
            from .ics import save_ics

            result["ics"] = str(save_ics(talks, out / "talks.ics"))
            progress.advance(progress.add_task("日历", total=1))

        if want_zip:
            st = progress.add_task("打包", total=1)
            zip_path = out.parent / f"{out.name}-{datetime.now():%Y%m%d-%H%M}.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in out.rglob("*"):
                    if f.is_file():
                        zf.write(f, f.relative_to(out.parent))
            result["zip"] = str(zip_path)
            progress.advance(st)

    return result


@app.command()
def gen(
    start: int = typer.Option(136991, "--start", "-s", help="起始宣讲会 id"),
    count: int = typer.Option(6, "--count", "-n", help="从 start 往后生成多少个"),
    ids: str = typer.Option("", "--ids", help="指定 id，逗号分隔，也可直接粘详情页链接"),
    csv: Path = typer.Option(None, "--csv", help="从 CSV 读取（company/date/location 等）"),
    demo: bool = typer.Option(False, "--demo", help="用演示数据跑一遍（不访问任何真实接口）"),
    out: Path = typer.Option(Path("out"), "--out", "-o", help="输出目录"),
    theme: str = typer.Option("hdu", "--theme", "-t", help=f"配色：{', '.join(theme_names())}"),
    module: str = typer.Option("rounded", "--module", help=f"模块形状：{', '.join(MODULE_STYLES)}"),
    eye: str = typer.Option("rounded", "--eye", help=f"定位点形状：{', '.join(EYE_STYLES)}"),
    scale: int = typer.Option(12, "--scale", help="每模块像素（越大越清晰）"),
    gradient: bool = typer.Option(False, "--gradient", help="渐变填充"),
    logo: Path = typer.Option(None, "--logo", help="中心 logo 图片"),
    no_card: bool = typer.Option(False, "--no-card", help="只出纯二维码，不画信息卡片"),
    sheet_flag: bool = typer.Option(True, "--sheet/--no-sheet", help="生成 A4 拼版"),
    pdf: bool = typer.Option(True, "--pdf/--no-pdf", help="同时导出 A4 PDF"),
    wall_flag: bool = typer.Option(True, "--wall/--no-wall", help="生成长图"),
    svg: bool = typer.Option(False, "--svg", help="额外导出矢量 SVG"),
    ics: bool = typer.Option(False, "--ics", help="导出 .ics 日历"),
    zip_out: bool = typer.Option(False, "--zip", help="打包成 zip"),
    verify: bool = typer.Option(True, "--verify/--no-verify", help="生成后用 zxing 反解自检"),
    clean: bool = typer.Option(True, "--clean/--keep", help="清理旧输出"),
    probe_ids: bool = typer.Option(False, "--probe", help="逐个请求签到 URL 探测 id 是否有效（可选，慢）"),
    json_out: bool = typer.Option(False, "--json", help="以 JSON 输出结果，便于脚本调用"),
    title: str = typer.Option("宣讲会签到码", "--title", help="标题（画廊/拼版页脚）"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="少说话"),
) -> None:
    """批量生成签到码：PNG 卡片 + A4 拼版 + 长图 + 网页画廊 + 清单。"""
    _utf8()
    if csv:
        # CSV 既是"清单"也是"元信息源"：只给 --ids 时才用 CSV 的元信息去补全
        meta = resolve(csv_path=csv)
        talks = merge_meta(meta, resolve(ids=ids)) if ids else meta
    else:
        talks = resolve(start=start, count=count, ids=ids, demo=demo)

    if not talks:
        console.print("[red]没有可生成的条目，检查 --start/--count/--ids/--csv[/red]")
        raise typer.Exit(2)

    talks = sort_talks(talks)
    style = _style(
        module=module,
        eye=eye,
        scale=max(4, scale),
        gradient=gradient,
        logo=str(logo) if logo else None,
        card=not no_card,
    )

    if not quiet and not json_out:
        console.print(Panel.fit(
            f"[bold]{BANNER.strip()}[/bold]\n"
            f"[dim]v{__version__} · 共 {len(talks)} 场 · 主题 {get_theme(theme).name} · "
            f"形状 {module}/{eye}{' · 渐变' if gradient else ''}[/dim]",
            border_style="cyan",
            padding=(0, 2),
        ))
        console.print(_summary_table(talks))

    t0 = time.time()
    result = _render_all(
        talks,
        out=out,
        theme_key=theme,
        style=style,
        want_sheet=sheet_flag,
        want_pdf=pdf and sheet_flag,
        want_wall=wall_flag,
        want_svg=svg,
        want_ics=ics,
        want_zip=zip_out,
        clean=clean,
        quiet=quiet or json_out,
        verify=verify and not json_out,
        title=title,
    )

    if probe_ids:
        console.print("[dim]正在探测 id 有效性…[/dim]")
        result["probe"] = probe(talks)

    elapsed = time.time() - t0

    if json_out:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    tree = Tree(f"[bold green]完成[/bold green] [dim]{elapsed:.1f}s[/dim]")
    tree.add(f"二维码卡片 [dim]{len(result['qr'])} 张[/dim] → [cyan]{out / 'qr'}[/cyan]")
    if result.get("sheet"):
        tree.add(f"A4 拼版 [dim]{len(result['sheet'])} 页[/dim] → [cyan]{out / 'sheet'}[/cyan]")
    if result.get("pdf"):
        tree.add(f"PDF → [cyan]{result['pdf']}[/cyan]")
    if result.get("wall"):
        tree.add(f"长图 → [cyan]{result['wall']}[/cyan]")
    tree.add(f"网页画廊 → [cyan]{result['gallery']}[/cyan]")
    tree.add(f"清单 → [cyan]{out / 'codes.csv'}[/cyan]")
    if result.get("ics"):
        tree.add(f"日历 → [cyan]{result['ics']}[/cyan]")
    if result.get("zip"):
        tree.add(f"压缩包 → [cyan]{result['zip']}[/cyan]")
    if verify:
        ok = result["verified"]
        color = "green" if ok == len(talks) else "yellow"
        tree.add(f"扫码自检 [{color}]{ok}/{len(talks)}[/{color}]")
    console.print(tree)

    for err in result["errors"]:
        console.print(f"[yellow]![/yellow] {err}")

    console.print(
        f"\n[dim]下一步：双击 [bold]{result['gallery']}[/bold] 预览；"
        f"或运行 [bold]xuanjqd preview[/bold] 打开可视化设计器。[/dim]"
    )


@app.command()
def demo(
    out: Path = typer.Option(Path("out"), "--out", "-o"),
    theme: str = typer.Option("hdu", "--theme", "-t"),
    quiet: bool = typer.Option(False, "--quiet", "-q"),
) -> None:
    """用 8 条演示数据一键出全套物料（截图 / 验收用）。"""
    _utf8()
    talks = sort_talks(demo_talks())
    style = QRStyle(module="rounded", eye="rounded", scale=12, gradient=True)
    result = _render_all(
        talks, out=out, theme_key=theme, style=style,
        want_sheet=True, want_pdf=True, want_wall=True, want_svg=True,
        want_ics=True, want_zip=False, clean=True, quiet=quiet, verify=True,
        title="本周校园宣讲会签到码",
    )
    if not quiet:
        console.print(Panel.fit(
            f"[bold green]演示数据已生成[/bold green]\n"
            f"{len(result['qr'])} 张卡片 · {len(result.get('sheet', []))} 页 A4 · 自检 {result['verified']}/{len(talks)}\n"
            f"打开：[cyan]{result['gallery']}[/cyan]",
            border_style="green",
        ))


@app.command()
def show(
    talk_id: int = typer.Argument(..., help="宣讲会 id"),
    theme: str = typer.Option("hdu", "--theme", "-t"),
) -> None:
    """在终端里直接看二维码（ASCII）+ 链接。"""
    _utf8()
    t = Talk(id=talk_id, company=f"宣讲会 #{talk_id}")
    console.print(Panel.fit(
        f"[bold]{t.display_name}[/bold]\n[dim]{t.signin_url}[/dim]",
        border_style="cyan",
    ))
    color = get_theme(theme).dark
    for line in ascii_art(t.signin_url, quiet=2):
        console.print(Text(line, style=color))


@app.command()
def preview(
    port: int = typer.Option(8848, "--port", "-p"),
    host: str = typer.Option("127.0.0.1", "--host"),
    open_browser: bool = typer.Option(True, "--open/--no-open"),
) -> None:
    """启动本地可视化设计器（改样式 → 实时预览 → 一键下载）。"""
    _utf8()
    try:
        import uvicorn  # noqa: F401
    except ImportError:
        console.print("[red]缺少依赖：pip install 'xuanjqd[web]'[/red]")
        raise typer.Exit(2)

    from .web.app import create_app

    console.print(Panel.fit(
        f"[bold]设计器已启动[/bold]\nhttp://{host}:{port}\n[dim]Ctrl+C 退出[/dim]",
        border_style="green",
    ))
    if open_browser:
        import threading
        import webbrowser

        threading.Timer(1.2, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    uvicorn.run(create_app(), host=host, port=port, log_level="warning")


@app.command()
def doctor() -> None:
    """环境自检：依赖、字体、扫码器、目录权限。"""
    _utf8()
    from .qr import _FONT_CANDIDATES

    table = Table(title="环境自检", box=None)
    table.add_column("项目", style="cyan")
    table.add_column("状态")
    table.add_column("说明", style="dim")

    def row(name: str, ok: bool, note: str = "") -> None:
        table.add_row(name, "[green]OK[/green]" if ok else "[yellow]缺失[/yellow]", note)

    import platform

    row("Python", sys.version_info >= (3, 9), platform.python_version())
    for mod in ("segno", "PIL", "rich", "typer", "qrcode"):
        try:
            __import__(mod)
            row(mod, True)
        except ImportError:
            row(mod, False, "pip install -r requirements.txt")

    font = next((p for p in _FONT_CANDIDATES if Path(p).exists()), None)
    row("中文字体", bool(font), font or "将退回默认字体，中文可能显示为方块")
    row("扫码自检 zxing-cpp", HAS_ZXING, "未安装时 --verify 会自动跳过")

    try:
        test = Talk(id=1)
        img = render(test, "hdu", QRStyle(scale=6, card=False))
        v = verify_payload(img, test.signin_url)
        row("渲染+回读", v.ok, v.reason or "ok")
    except Exception as exc:  # noqa: BLE001
        row("渲染+回读", False, str(exc))

    console.print(table)


@app.command()
def themes() -> None:
    """看看有哪些配色。"""
    _utf8()
    table = Table(box=None, title="配色主题")
    table.add_column("key", style="cyan")
    table.add_column("名称")
    table.add_column("主色")
    table.add_column("渐变色")
    for key, th in THEMES.items():
        table.add_row(key, th.name, f"[{th.dark}]■[/] {th.dark}", f"[{th.dark2}]■[/] {th.dark2}")
    console.print(table)


def main() -> None:
    _utf8()
    app()


if __name__ == "__main__":
    main()
