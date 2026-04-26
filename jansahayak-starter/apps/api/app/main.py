from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
from pathlib import Path

from .core.config import get_settings
from .routes.chat import router as chat_router
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
app.mount("/public", StaticFiles(directory=public_dir), name="public")


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
