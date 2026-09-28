from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal, init_db
from app.models import User, UserRole
from app.api.routes import router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered pharmaceutical complaint management system",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix=settings.api_prefix)


def seed_admin():
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == "admin@aivoa.com").first():
            db.add(
                User(
                    email="admin@aivoa.com",
                    full_name="AIVOA Admin",
                    hashed_password=hash_password("admin123"),
                    role=UserRole.ADMIN,
                )
            )
            db.add(
                User(
                    email="qa@aivoa.com",
                    full_name="QA Manager",
                    hashed_password=hash_password("qa123456"),
                    role=UserRole.QA_MANAGER,
                )
            )
            db.commit()
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    from app.core.config import clear_settings_cache

    clear_settings_cache()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

    init_db()
    seed_admin()



@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "api": settings.api_prefix,
    }
