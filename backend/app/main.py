"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app import __version__
from app.api.admin_audit import router as admin_audit_router
from app.api.admin_categories import router as admin_categories_router
from app.api.admin_jobs import router as admin_jobs_router
from app.api.admin_photos import router as admin_photos_router
from app.api.admin_users import router as admin_users_router
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.map import router as map_router
from app.api.photos import router as photos_router
from app.api.showcase import router as showcase_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    application = FastAPI(title="KinFrame API", version=__version__)
    application.include_router(health_router)
    application.include_router(map_router)
    application.include_router(auth_router)
    application.include_router(admin_users_router)
    application.include_router(admin_jobs_router)
    application.include_router(admin_photos_router)
    application.include_router(admin_categories_router)
    application.include_router(admin_audit_router)
    application.include_router(photos_router)
    application.include_router(showcase_router)
    return application


app = create_app()
