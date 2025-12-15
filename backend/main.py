import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import FileResponse, PlainTextResponse

from backend.core.config import settings
from backend.core.logging_config import setup_logging
from backend.api.middleware import RequestLoggingMiddleware
from backend.api.redis_rate_limit_middleware import RedisRateLimitMiddleware
from backend.api.workspace_middleware import WorkspaceContextMiddleware
from backend.api.routes import (
    auth,
    auth_enterprise,
    workspaces,
    clones,
    memories,
    conversations,
    documents,
    chat,
    health,
    api_keys,
    admin,
)
from backend.core.redis_client import close_redis


# ============================================================
# LOGGING CONFIG
# ============================================================
setup_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)
logger = logging.getLogger(__name__)
logger.info("MAIN_MODULE_LOADED", extra={"file": __file__})


# ============================================================
# LIFESPAN
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "APPLICATION_STARTUP",
        extra={
            "project_name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "llm_provider": settings.LLM_PROVIDER,
        },
    )
    yield
    logger.info("APPLICATION_SHUTDOWN")
    close_redis()


# ============================================================
# APP INIT
# ============================================================
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)


# ============================================================
# CORS — DOIT ÊTRE LE PREMIER MIDDLEWARE
# ============================================================
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "https://localhost:3000",
    "https://clonememoria-frontend.onrender.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "X-Request-ID",
    ],
    max_age=600,
)


# ============================================================
# AUTRES MIDDLEWARES (APRÈS CORS)
# ============================================================
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(WorkspaceContextMiddleware, enabled=True)
app.add_middleware(RedisRateLimitMiddleware, enabled=True)


# ============================================================
# TRUSTED HOSTS
# ============================================================
TRUSTED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "*.localhost",
    "*.onrender.com",
    "clonememoria-backend.onrender.com",
    "*",
]

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=TRUSTED_HOSTS,
)

logger.info(
    "SECURITY_MIDDLEWARE_CONFIGURED",
    extra={
        "allowed_origins": ALLOWED_ORIGINS,
        "trusted_hosts": TRUSTED_HOSTS,
        "rate_limiting_enabled": True,
    },
)


# ============================================================
# SECURITY HEADERS
# ============================================================
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

    response.headers["Content-Security-Policy"] = "; ".join(
        [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self' https://gniuyicdmjmzbgwbnvmk.supabase.co",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
    )

    return response


logger.info("CONTENT_SECURITY_POLICY_CONFIGURED")


# ============================================================
# ROUTES
# ============================================================
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["auth"])
app.include_router(
    auth_enterprise.router,
    prefix=f"{settings.API_V1_PREFIX}/auth-v2",
    tags=["auth-enterprise"],
)
app.include_router(
    workspaces.router,
    prefix=f"{settings.API_V1_PREFIX}/workspaces",
    tags=["workspaces"],
)
app.include_router(
    clones.router,
    prefix=f"{settings.API_V1_PREFIX}/clones",
    tags=["clones"],
)
app.include_router(
    memories.router,
    prefix=f"{settings.API_V1_PREFIX}/clones/{{clone_id}}/memories",
    tags=["memories"],
)
app.include_router(
    conversations.router,
    prefix=f"{settings.API_V1_PREFIX}/clones/{{clone_id}}/conversations",
    tags=["conversations"],
)
app.include_router(
    documents.router,
    prefix=f"{settings.API_V1_PREFIX}/clones/{{clone_id}}/documents",
    tags=["documents"],
)
app.include_router(chat.router, prefix=f"{settings.API_V1_PREFIX}/chat", tags=["chat"])
app.include_router(health.router, tags=["health"])
app.include_router(api_keys.router, prefix=f"{settings.API_V1_PREFIX}", tags=["api-keys"])
app.include_router(admin.router, prefix=f"{settings.API_V1_PREFIX}", tags=["admin"])

logger.info("API_ROUTES_REGISTERED", extra={"api_prefix": settings.API_V1_PREFIX})


# ============================================================
# ROOT / FAVICON / ROBOTS
# ============================================================
@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs": "/docs",
    }


@app.head("/")
async def head_root():
    return Response(status_code=200)


FAVICON_PATH = os.path.join(os.path.dirname(__file__), "static", "favicon.ico")


@app.get("/favicon.ico")
async def favicon():
    if os.path.exists(FAVICON_PATH):
        return FileResponse(FAVICON_PATH, media_type="image/x-icon")
    return Response(status_code=204)


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots():
    return "User-agent: *\nDisallow: /"


# ============================================================
# LOCAL DEV
# ============================================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None,
    )
