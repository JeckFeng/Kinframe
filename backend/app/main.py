"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app import __version__
from app.api.admin_users import router as admin_users_router
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.photos import router as photos_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    application = FastAPI(title="KinFrame API", version=__version__)
    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(admin_users_router)
    application.include_router(photos_router)
    return application


app = create_app()
