"""本地 Web 界面：抓取 → 按天挑选 → 生成签到码。"""

from __future__ import annotations

import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .. import crawl as crawler
from ..codec import signin_url
from ..models import Talk, from_range
from ..qr import EYE_STYLES, MODULE_STYLES, QRStyle, render, to_png_bytes
from ..theme import THEMES

HERE = Path(__file__).parent
STATIC = HERE / "static"
LOGO = HERE.parent / "assets" / "logo.png"
OUT = Path("out").resolve()

_lock = threading.Lock()
_state: dict[str, Any] = {"talks": [], "fetched_at": None, "error": ""}


def _talk_dict(t: Talk) -> dict[str, Any]:
    return {
        "id": t.id,
        "company": t.display_name,
        "date": t.start_at.strftime("%Y-%m-%d") if t.start_at else "",
        "date_label": t.date_label,
        "time": t.start_at.strftime("%H:%M") if t.start_at else "",
        "location": t.location,
        "status": t.status,
        "url": t.url,
        "signin_url": t.signin_url,
    }


def _refresh() -> dict[str, Any]:
    try:
        talks = crawler.crawl()
        crawler.save_cache(talks)
        _state.update(talks=talks, fetched_at=datetime.now(), error="")
    except Exception as exc:  # noqa: BLE001
        cached, when = crawler.load_cache()
        _state.update(talks=cached, fetched_at=when, error=f"抓取失败：{exc}")
    return _state


def _ensure() -> dict[str, Any]:
    if not _state["talks"]:
        cached, when = crawler.load_cache()
        if cached:
            _state.update(talks=cached, fetched_at=when)
        else:
            _refresh()
    return _state


def create_app() -> FastAPI:
    app = FastAPI(title="宣讲会签到码", docs_url="/api/docs", redoc_url=None)

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    @app.get("/api/talks")
    def talks(refresh: int = Query(0)) -> JSONResponse:
        st = _refresh() if refresh else _ensure()
        talks_list = st["talks"]
        days: dict[str, int] = {}
        for t in talks_list:
            key = t.start_at.strftime("%Y-%m-%d") if t.start_at else ""
            if key:
                days[key] = days.get(key, 0) + 1
        return JSONResponse(
            {
                "ok": not st["error"],
                "error": st["error"],
                "fetched_at": st["fetched_at"].strftime("%Y-%m-%d %H:%M") if st["fetched_at"] else "",
                "source": "job.hdu.edu.cn",
                "days": [{"date": k, "count": v} for k, v in sorted(days.items())],
                "talks": [_talk_dict(t) for t in talks_list],
            }
        )

    @app.get("/api/preview.png")
    def preview(
        id: int = Query(137324),
        theme: str = Query("hdu"),
        module: str = Query("rounded"),
        eye: str = Query("rounded"),
        gradient: bool = Query(True),
        logo: bool = Query(False),
    ) -> Response:
        style = QRStyle(
            module=module if module in MODULE_STYLES else "rounded",
            eye=eye if eye in EYE_STYLES else "rounded",
            scale=12,
            gradient=gradient,
            logo=str(LOGO) if (logo and LOGO.exists()) else None,
        )
        pool = {t.id: t for t in _ensure()["talks"]}
        talk = pool.get(id) or Talk(id=id, company=f"宣讲会 #{id}")
        return Response(content=to_png_bytes(render(talk, theme, style)), media_type="image/png")

    @app.get("/api/link")
    def link(id: int = Query(137324)) -> JSONResponse:
        return JSONResponse({"id": id, "url": signin_url(id)})

    @app.post("/api/generate")
    def generate(payload: dict) -> JSONResponse:
        ids = [int(i) for i in payload.get("ids") or []]
        start = payload.get("start")
        count = payload.get("count")

        talks: list[Talk] = []
        if ids:
            pool = {t.id: t for t in _ensure()["talks"]}
            talks = [pool.get(i) or Talk(id=i) for i in ids]
        elif start and count:
            talks = from_range(int(start), int(count))
        if not talks:
            raise HTTPException(400, "没有选中任何宣讲会")

        with _lock:
            from ..cli import _render_all

            if OUT.exists():
                shutil.rmtree(OUT, ignore_errors=True)
            result = _render_all(
                talks,
                out=OUT,
                theme_key=str(payload.get("theme") or "hdu"),
                style=QRStyle(
                    module=str(payload.get("module") or "rounded"),
                    eye=str(payload.get("eye") or "rounded"),
                    scale=12,
                    gradient=bool(payload.get("gradient", True)),
                    logo=str(LOGO) if payload.get("logo") and LOGO.exists() else None,
                ),
                want_sheet=True,
                want_pdf=True,
                want_wall=True,
                want_svg=False,
                want_ics=True,
                want_zip=True,
                clean=True,
                quiet=True,
                verify=True,
                title="宣讲会签到码",
            )

        files = []
        if OUT.exists():
            for f in sorted(OUT.rglob("*")):
                if f.is_file() and f.suffix.lower() in {".png", ".pdf", ".html", ".csv"}:
                    files.append({"name": str(f.relative_to(OUT)).replace("\\", "/"), "size": f.stat().st_size})

        return JSONResponse(
            {
                "ok": True,
                "count": len(talks),
                "verified": result.get("verified", 0),
                "zip": Path(result["zip"]).name if result.get("zip") else "",
                "files": files,
                "gallery": "index.html",
            }
        )

    @app.get("/api/file")
    def file(p: str = Query(...)) -> FileResponse:
        target = (OUT / p).resolve()
        if not str(target).startswith(str(OUT)) or not target.is_file():
            raise HTTPException(404, "not found")
        return FileResponse(target)

    @app.get("/api/zip")
    def zip_file() -> FileResponse:
        zips = sorted(OUT.parent.glob("out-*.zip"), key=lambda x: x.stat().st_mtime, reverse=True)
        if not zips:
            raise HTTPException(404, "还没有生成压缩包")
        return FileResponse(zips[0], filename=zips[0].name)

    if STATIC.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

    return app


app = create_app()
