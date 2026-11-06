"""本地可视化设计器：左边调参数，右边实时出图，满意了直接下载。

    xuanjqd preview            # 打开 http://127.0.0.1:8848
"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from ..codec import signin_url
from ..models import Talk, demo_talks
from ..qr import EYE_STYLES, MODULE_STYLES, QRStyle, render, to_png_bytes
from ..theme import THEMES, get_theme

HERE = Path(__file__).parent
STATIC = HERE / "static"
LOGO = HERE.parent / "assets" / "logo.png"


def _talk(
    id: int,
    company: str,
    title: str,
    date: str,
    time: str,
    location: str,
) -> Talk:
    start = None
    if date:
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                raw = f"{date} {time}".strip() if time else date
                start = datetime.strptime(raw, fmt if time else "%Y-%m-%d")
                break
            except ValueError:
                continue
    return Talk(id=id, company=company, title=title or "校园宣讲会", start_at=start, location=location)


def create_app() -> FastAPI:
    app = FastAPI(title="xuanjqd 设计器", docs_url="/api/docs", redoc_url=None)

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    @app.get("/api/themes")
    def themes() -> JSONResponse:
        return JSONResponse(
            [
                {"key": k, "name": v.name, "dark": v.dark, "dark2": v.dark2}
                for k, v in THEMES.items()
            ]
        )

    @app.get("/api/talks")
    def talks() -> JSONResponse:
        return JSONResponse([t.to_json() for t in demo_talks()])

    @app.get("/api/preview.png")
    def preview(
        id: int = Query(136991),
        company: str = Query("浙江明贺钢管有限公司"),
        title: str = Query("2026 届校园宣讲会"),
        date: str = Query(""),
        time: str = Query("14:00"),
        location: str = Query("6 教中 325"),
        theme: str = Query("hdu"),
        module: str = Query("rounded"),
        eye: str = Query("rounded"),
        gradient: bool = Query(False),
        logo: bool = Query(False),
        card: bool = Query(True),
        scale: int = Query(12, ge=4, le=24),
    ) -> Response:
        style = QRStyle(
            module=module if module in MODULE_STYLES else "rounded",
            eye=eye if eye in EYE_STYLES else "rounded",
            scale=scale,
            gradient=gradient,
            logo=str(LOGO) if (logo and LOGO.exists()) else None,
            card=card,
            shadow=card,
        )
        talk = _talk(id, company, title, date, time, location)
        img = render(talk, theme, style)
        return Response(content=to_png_bytes(img), media_type="image/png")

    @app.get("/api/link")
    def link(id: int = Query(136991)) -> JSONResponse:
        return JSONResponse({"id": id, "url": signin_url(id)})

    if STATIC.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

    return app


app = create_app()
