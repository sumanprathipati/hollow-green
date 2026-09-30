"""FastAPI app factory."""

from fastapi import FastAPI

from api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="hollow-green")
    app.include_router(router)
    return app


app = create_app()
