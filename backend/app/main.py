from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import Settings, settings

_CORS_ALLOWED_METHODS = ("GET", "HEAD", "OPTIONS", "POST")
_CORS_ALLOWED_HEADERS = ("Accept", "Content-Type")


def apply_cors(application: FastAPI, app_settings: Settings) -> None:
    """Attach settings-backed CORS for the configured browser API surface."""
    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_allowed_origins,
        allow_credentials=False,
        allow_methods=list(_CORS_ALLOWED_METHODS),
        allow_headers=list(_CORS_ALLOWED_HEADERS),
    )


app = FastAPI(title=settings.app_title)
apply_cors(app, settings)
app.include_router(v1_router, prefix=settings.api_v1_prefix)
