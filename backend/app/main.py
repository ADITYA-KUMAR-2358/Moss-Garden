"""HTTP entrypoint."""

import logging
from pathlib import Path
from urllib.parse import urlsplit

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


CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob: https://github.com https://avatars.githubusercontent.com",
        "media-src 'self' blob:",
        "font-src 'self' data:",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self' https://github.com",
        "frame-ancestors 'none'",
    )
)


def security_headers(production: bool) -> dict[str, str]:
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
        "Cross-Origin-Opener-Policy": "same-origin",
    }
    if production:
        # The local GitHub App setup page posts an inline-scripted form, so CSP and HSTS apply in production only.
        headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return headers


UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def cross_site_write(request: Request) -> bool:
    """SameSite=Lax already keeps the session cookie off cross-site writes; this refuses them outright."""
    if request.method not in UNSAFE_METHODS or not request.url.path.startswith("/api/"):
        return False
    if request.url.path == "/api/jobs/nightly":
        return False
    origin = request.headers.get("origin")
    if not origin:
        return False
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    return urlsplit(origin).netloc.lower() != host.lower()


def create_app() -> FastAPI:
    production = get_settings().environment == "production"
    app = FastAPI(
        title="Moss Garden",
        docs_url=None if production else "/docs",
        redoc_url=None if production else "/redoc",
        openapi_url=None if production else "/openapi.json",
    )
    app.include_router(router)

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        if cross_site_write(request):
            response = JSONResponse({"detail": "Cross-site request refused"}, status_code=403)
        else:
            response = await call_next(request)
        for name, value in security_headers(get_settings().environment == "production").items():
            response.headers.setdefault(name, value)
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

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
        # Asset names change on every build, so the page that lists them must be revalidated.
        return FileResponse(page, headers={"Cache-Control": "no-cache"})

    assets = DIST / "assets"
    audio = DIST / "audio"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")
    if audio.exists():
        app.mount("/audio", StaticFiles(directory=audio), name="audio")
    return app


app = create_app()
