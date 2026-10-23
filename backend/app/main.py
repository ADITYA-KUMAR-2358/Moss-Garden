"""HTTP entrypoint."""

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import get_settings
from app.db import get_engine, get_sessionmaker
from app.models import Base
from app.services.seed import seed_demo

logger = logging.getLogger(__name__)
DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
PUBLIC = Path(__file__).resolve().parents[2] / "frontend" / "public"
ICONS = {
    "favicon.ico": "image/x-icon",
    "favicon.svg": "image/svg+xml",
    "favicon-32.png": "image/png",
    "apple-touch-icon.png": "image/png",
}


def create_app() -> FastAPI:
    app = FastAPI(title="Moss Garden")
    app.include_router(router)

    @app.on_event("startup")
    def startup() -> None:
        settings = get_settings()
        if not settings.database_url:
            return
        try:
            engine = get_engine()
            Base.metadata.create_all(engine)
            if settings.demo_seed:
                session = get_sessionmaker()()
                try:
                    seed_demo(session)
                    session.commit()
                finally:
                    session.close()
        except Exception:
            logger.exception("database init failed")

    @app.get("/favicon.ico", include_in_schema=False)
    @app.get("/favicon.svg", include_in_schema=False)
    @app.get("/favicon-32.png", include_in_schema=False)
    @app.get("/apple-touch-icon.png", include_in_schema=False)
    def icon(request: Request):
        name = Path(request.url.path).name
        for root in (PUBLIC, DIST):
            file = root / name
            if file.is_file():
                return FileResponse(file, media_type=ICONS.get(name))
        return JSONResponse({"detail": "Icon is missing"}, status_code=404)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/")
    def index():
        page = DIST / "index.html"
        if not page.exists():
            return JSONResponse(
                {"detail": "React build is missing. From frontend/, run npm install and npm run build."},
                status_code=503,
            )
        return FileResponse(page)

    assets = DIST / "assets"
    audio = DIST / "audio"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")
    if audio.exists():
        app.mount("/audio", StaticFiles(directory=audio), name="audio")
    return app


app = create_app()
