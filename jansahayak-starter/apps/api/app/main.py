from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
import logging
from pathlib import Path
import time

from .core.config import get_settings
from .routes.chat import router as chat_router
from .routes.inspector import record_event, router as inspector_router
from .routes.voice import router as voice_router
from .routes.whatsapp import router as whatsapp_router, twilio_webhook

settings = get_settings()
logging.basicConfig(level=logging.INFO if settings.debug else logging.WARNING, format="%(asctime)s %(levelname)s %(name)s %(message)s")
app = FastAPI(title=settings.app_name, debug=settings.debug)
public_dir = Path(__file__).resolve().parents[3] / "public"
public_dir.mkdir(parents=True, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(voice_router)
app.include_router(whatsapp_router)
app.include_router(inspector_router)
app.mount("/public", StaticFiles(directory=public_dir), name="public")


@app.middleware("http")
async def capture_requests(request: Request, call_next):
    path = request.url.path
    if path.startswith("/debug/inspector") or path.startswith("/public/audio/"):
        return await call_next(request)

    started_at = time.perf_counter()
    request_body = await request.body()

    async def receive():
        return {"type": "http.request", "body": request_body, "more_body": False}

    cloned_request = Request(request.scope, receive)
    response = await call_next(cloned_request)
    response_body = b""
    async for chunk in response.body_iterator:
        response_body += chunk

    duration_ms = (time.perf_counter() - started_at) * 1000
    record_event(
        method=request.method,
        path=path,
        query_string=request.url.query,
        request_headers=dict(request.headers),
        request_body=request_body,
        response_status=response.status_code,
        response_headers=dict(response.headers),
        response_body=response_body,
        duration_ms=duration_ms,
    )

    return Response(
        content=response_body,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type,
    )


@app.get("/")
def health():
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}


@app.post("/")
async def twilio_root_alias(request: Request):
    """
    Temporary compatibility alias for Twilio webhook misconfiguration.
    Prefer configuring Twilio to call /whatsapp/twilio directly.
    """
    return await twilio_webhook(request)
