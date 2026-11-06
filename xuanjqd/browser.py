"""打开浏览器的小工具。

Windows 上如果 Edge 是以管理员身份运行的，普通权限进程再调 `start url`
会被 Edge 的实例单例挡住，弹「是否用普通权限重启现有实例」的框——
点"是"会把用户正在用的浏览器重启掉。

所以这里优先用独立的 user-data-dir 起一个新窗口：不影响用户已有的标签页，
也不会触发那个提示。实在不行再退回系统默认浏览器。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

_WIN_BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def _profile_dir() -> Path:
    """找一个能写的目录放浏览器配置，按优先级回退。"""
    import tempfile

    candidates = [
        Path(os.environ.get("LOCALAPPDATA") or "") / "xuanjqd" / "browser",
        Path(tempfile.gettempdir()) / "xuanjqd-browser",
        Path.cwd() / ".xuanjqd-browser",
    ]
    for path in candidates:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return path
        except OSError:
            continue
    return Path.cwd()


def _copy_to_clipboard(text: str) -> bool:
    if os.name != "nt":
        return False
    try:
        subprocess.run("clip", input=text.encode("utf-16-le"), check=True, shell=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:  # noqa: BLE001
        return False


def open_url(url: str, *, isolated: bool = True) -> str:
    """打开 url，返回实际用的方式：edge / chrome / default / manual。"""
    if os.name == "nt":
        for exe in _WIN_BROWSERS:
            if not os.path.exists(exe):
                continue
            args = [exe, "--no-first-run", "--no-default-browser-check"]
            if isolated:
                args.append(f"--user-data-dir={_profile_dir()}")
            args += ["--new-window", url]
            try:
                subprocess.Popen(
                    args,
                    close_fds=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
                )
                return "edge" if "msedge" in exe else "chrome"
            except OSError:
                continue

    try:
        if webbrowser.open(url):
            return "default"
    except Exception:  # noqa: BLE001
        pass

    _copy_to_clipboard(url)
    return "manual"


def free_port(host: str, port: int, tries: int = 20) -> int:
    """端口被占用就往后找一个空闲的。"""
    import socket

    for candidate in range(port, port + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, candidate))
            except OSError:
                continue
            return candidate
    return port
