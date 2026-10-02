"""FastAPI app factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.demo_releases import demo_router
from api.evidence_review import review_router
from api.public_data import public_router
from api.routes import router
from api.settings import allowed_origins, log_safe_config


def create_app() -> FastAPI:
    app = FastAPI(title="hollow-green")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins(),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["content-type"],
        allow_credentials=False,
        max_age=600,
    )
    log_safe_config()
    app.include_router(router)
    app.include_router(demo_router)
    app.include_router(public_router)
    app.include_router(review_router)
    return app


app = create_app()
