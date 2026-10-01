"""FastAPI app factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.demo_releases import ALLOWED_ORIGINS, demo_router
from api.public_data import public_router
from api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="hollow-green")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["content-type"],
        allow_credentials=False,
        max_age=600,
    )
    app.include_router(router)
    app.include_router(demo_router)
    app.include_router(public_router)
    return app


app = create_app()
