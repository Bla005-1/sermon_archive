import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from app.api.router import api_router
from app.config import settings
from app.services import index_sync_service


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.index_sync_dispatch_enabled:
        index_sync_service.start_dispatcher()
    try:
        yield
    finally:
        if settings.index_sync_dispatch_enabled:
            index_sync_service.stop_dispatcher()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application for current runtime mode."""
    if not settings.debug:
        logging.basicConfig(filename='app.log', level=getattr(logging, settings.log_level, logging.INFO))

    app = FastAPI(
        title="Sermon Archive API",
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(ProxyHeadersMiddleware)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    return app


app = create_app()
